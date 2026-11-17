"""
FitTrack - Gym Management System
================================
Main Application Module (Flask Web Server)

TECH STACK:
- Backend: Python Flask
- SQL Database: MySQL (PyMySQL) - ACID Compliant, Normalized Core Tables
- NoSQL Database: MongoDB (PyMongo) - Flexible Document Store for Workouts & Metrics
- Frontend: HTML5, CSS3, JavaScript, Jinja2 Templates, Chart.js

DBMS CONCEPTS IMPLEMENTED:
1. Polyglot Persistence: Combining relational SQL with NoSQL document storage.
2. Parameterized Queries: All MySQL interactions use '%s' placeholders to prevent SQL Injection.
3. Normalization & Constraints: NOT NULL, UNIQUE, FOREIGN KEY with ON DELETE SET NULL.
4. Flexible Schemas: Embedded arrays and sub-documents in MongoDB.
5. Aggregations: SQL GROUP BY + MongoDB Aggregation Pipelines ($group, $avg).
6. Cross-Database Hybrid Integration: Uniting SQL entities with NoSQL documents via member_id.
7. Audit Logging: Automatic system activity trail saved to MongoDB.
"""

import re
from datetime import datetime, date
from bson.objectid import ObjectId
from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify
)

from config import Config
from db import (
    get_mysql_connection, execute_query, get_mongo_db, log_activity, check_db_health
)

app = Flask(__name__)
app.config.from_object(Config)

# Simple regex for email format validation
EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


# ==============================================================================
# Context Processors & Middleware
# ==============================================================================

@app.context_processor
def inject_global_data():
    """
    Injects database health indicators and current date into all Jinja templates.
    Ensures connection failures are displayed transparently to the user.
    """
    health = check_db_health()
    return {
        "db_status": health,
        "today_date": date.today().isoformat()
    }


# ==============================================================================
# Helper Functions: Entity Lookups
# ==============================================================================

def get_members_dict():
    """Returns a dictionary of members {member_id: member_name} from MySQL."""
    try:
        rows = execute_query("SELECT member_id, name FROM members ORDER BY name ASC")
        return {r["member_id"]: r["name"] for r in (rows or [])}
    except Exception:
        return {}


def get_trainers_dict():
    """Returns a dictionary of trainers {trainer_id: trainer_name} from MySQL."""
    try:
        rows = execute_query("SELECT trainer_id, name FROM trainers ORDER BY name ASC")
        return {r["trainer_id"]: r["name"] for r in (rows or [])}
    except Exception:
        return {}


# ==============================================================================
# 1. Dashboard Route
# ==============================================================================

@app.route("/")
def dashboard():
    """
    System Dashboard:
    - SQL: Computes counts of members, trainers, plans, and classes using COUNT(*).
    - NoSQL: Computes total workout logs count and average trainer rating using MongoDB aggregations.
    - SQL: Fetches recent 5 registered members with plans and trainers via JOIN.
    - NoSQL: Fetches recent 6 audit logs from MongoDB activity_logs.
    """
    stats = {
        "members_count": 0,
        "trainers_count": 0,
        "plans_count": 0,
        "classes_count": 0,
        "workouts_count": 0,
        "avg_rating": 0.0
    }
    recent_members = []
    recent_activities = []

    # 1. SQL Aggregations & Recent Members
    try:
        conn = get_mysql_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS cnt FROM members")
                stats["members_count"] = cursor.fetchone()["cnt"]

                cursor.execute("SELECT COUNT(*) AS cnt FROM trainers")
                stats["trainers_count"] = cursor.fetchone()["cnt"]

                cursor.execute("SELECT COUNT(*) AS cnt FROM plans")
                stats["plans_count"] = cursor.fetchone()["cnt"]

                cursor.execute("SELECT COUNT(*) AS cnt FROM classes")
                stats["classes_count"] = cursor.fetchone()["cnt"]

                # Recent members with SQL JOIN
                cursor.execute("""
                    SELECT m.member_id, m.name, m.email, m.join_date,
                           p.plan_name, t.name AS trainer_name
                    FROM members m
                    LEFT JOIN plans p ON m.plan_id = p.plan_id
                    LEFT JOIN trainers t ON m.trainer_id = t.trainer_id
                    ORDER BY m.member_id DESC LIMIT 5
                """)
                recent_members = cursor.fetchall()
            conn.close()
    except Exception as e:
        flash(f"SQL Database Notice: {e}", "warning")

    # 2. NoSQL Aggregations & Recent Activities
    try:
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            # Workout count
            stats["workouts_count"] = mongo_db.workout_logs.count_documents({})

            # Average trainer rating from feedback collection
            pipeline = [
                {"$group": {"_id": None, "avgRating": {"$avg": "$rating"}}}
            ]
            agg = list(mongo_db.feedback.aggregate(pipeline))
            if agg and "avgRating" in agg[0] and agg[0]["avgRating"] is not None:
                stats["avg_rating"] = round(agg[0]["avgRating"], 1)

            # Recent activity logs
            recent_activities = list(
                mongo_db.activity_logs.find().sort("timestamp", -1).limit(6)
            )
    except Exception as e:
        flash(f"NoSQL Database Notice: {e}", "warning")

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        stats=stats,
        recent_members=recent_members,
        recent_activities=recent_activities
    )


# ==============================================================================
# 2. Members Management (SQL - Full CRUD)
# ==============================================================================

@app.route("/members")
def members_list():
    """List all members with SQL JOIN to plans and trainers, plus search filter."""
    search_query = request.args.get("q", "").strip()
    members = []
    try:
        if search_query:
            query = """
                SELECT m.*, p.plan_name, t.name AS trainer_name
                FROM members m
                LEFT JOIN plans p ON m.plan_id = p.plan_id
                LEFT JOIN trainers t ON m.trainer_id = t.trainer_id
                WHERE m.name LIKE %s OR m.email LIKE %s OR m.phone LIKE %s
                ORDER BY m.member_id DESC
            """
            like_param = f"%{search_query}%"
            members = execute_query(query, (like_param, like_param, like_param))
        else:
            query = """
                SELECT m.*, p.plan_name, t.name AS trainer_name
                FROM members m
                LEFT JOIN plans p ON m.plan_id = p.plan_id
                LEFT JOIN trainers t ON m.trainer_id = t.trainer_id
                ORDER BY m.member_id DESC
            """
            members = execute_query(query)
    except Exception as e:
        flash(f"Error fetching members: {e}", "danger")

    return render_template(
        "members/index.html",
        active_page="members",
        members=members,
        search_query=search_query
    )


@app.route("/members/add", methods=["GET", "POST"])
def members_add():
    """Add a new member with server-side validation and duplicate email check."""
    plans = execute_query("SELECT plan_id, plan_name, duration_months, price FROM plans ORDER BY price ASC") or []
    trainers = execute_query("SELECT trainer_id, name, specialization FROM trainers ORDER BY name ASC") or []

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        join_date = request.form.get("join_date", "").strip()
        plan_id = request.form.get("plan_id") or None
        trainer_id = request.form.get("trainer_id") or None

        # Server-side validation
        errors = []
        if not name:
            errors.append("Full Name is required.")
        if not email or not EMAIL_REGEX.match(email):
            errors.append("A valid Email Address is required.")
        if not phone:
            errors.append("Phone Number is required.")
        if not join_date:
            errors.append("Membership Join Date is required.")

        # Check for duplicate email (Enforcing UNIQUE constraint gracefully)
        if email:
            existing = execute_query(
                "SELECT member_id FROM members WHERE email = %s", (email,), fetch_one=True
            )
            if existing:
                errors.append(f"The email '{email}' is already registered to Member #{existing['member_id']}.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                "members/form.html",
                active_page="members",
                is_edit=False,
                plans=plans,
                trainers=trainers,
                form_data=request.form
            )

        # Parameterized INSERT query
        try:
            insert_query = """
                INSERT INTO members (name, email, phone, join_date, plan_id, trainer_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            new_id = execute_query(
                insert_query,
                (name, email, phone, join_date, plan_id, trainer_id),
                commit=True
            )
            flash(f"Member '{name}' registered successfully (Member ID #{new_id})!", "success")
            log_activity("CREATE", "Members", f"Added new member: {name} ({email}) with ID #{new_id}")
            return redirect(url_for("members_list"))
        except Exception as e:
            flash(f"Database error during registration: {e}", "danger")

    return render_template(
        "members/form.html",
        active_page="members",
        is_edit=False,
        plans=plans,
        trainers=trainers,
        form_data=None
    )


@app.route("/members/edit/<int:member_id>", methods=["GET", "POST"])
def members_edit(member_id):
    """Edit an existing member with parameterized UPDATE."""
    member = execute_query("SELECT * FROM members WHERE member_id = %s", (member_id,), fetch_one=True)
    if not member:
        flash(f"Member #{member_id} not found.", "danger")
        return redirect(url_for("members_list"))

    plans = execute_query("SELECT plan_id, plan_name, duration_months, price FROM plans ORDER BY price ASC") or []
    trainers = execute_query("SELECT trainer_id, name, specialization FROM trainers ORDER BY name ASC") or []

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        join_date = request.form.get("join_date", "").strip()
        plan_id = request.form.get("plan_id") or None
        trainer_id = request.form.get("trainer_id") or None

        errors = []
        if not name:
            errors.append("Full Name is required.")
        if not email or not EMAIL_REGEX.match(email):
            errors.append("A valid Email Address is required.")
        if not phone:
            errors.append("Phone Number is required.")
        if not join_date:
            errors.append("Join Date is required.")

        # Duplicate email check for OTHER members
        if email:
            existing = execute_query(
                "SELECT member_id FROM members WHERE email = %s AND member_id != %s",
                (email, member_id),
                fetch_one=True
            )
            if existing:
                errors.append(f"The email '{email}' is already in use by another member.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                "members/form.html",
                active_page="members",
                is_edit=True,
                member=member,
                plans=plans,
                trainers=trainers,
                form_data=request.form
            )

        try:
            update_query = """
                UPDATE members
                SET name = %s, email = %s, phone = %s, join_date = %s,
                    plan_id = %s, trainer_id = %s
                WHERE member_id = %s
            """
            execute_query(
                update_query,
                (name, email, phone, join_date, plan_id, trainer_id, member_id),
                commit=True
            )
            flash(f"Member #{member_id} ({name}) updated successfully!", "success")
            log_activity("UPDATE", "Members", f"Updated member profile: ID #{member_id} ({name})")
            return redirect(url_for("members_list"))
        except Exception as e:
            flash(f"Error updating member: {e}", "danger")

    return render_template(
        "members/form.html",
        active_page="members",
        is_edit=True,
        member=member,
        plans=plans,
        trainers=trainers,
        form_data=None
    )


@app.route("/members/delete/<int:member_id>", methods=["POST"])
def members_delete(member_id):
    """Delete a member from MySQL and log the action."""
    try:
        member = execute_query("SELECT name FROM members WHERE member_id = %s", (member_id,), fetch_one=True)
        name = member["name"] if member else f"ID #{member_id}"
        execute_query("DELETE FROM members WHERE member_id = %s", (member_id,), commit=True)
        flash(f"Member '{name}' deleted successfully.", "success")
        log_activity("DELETE", "Members", f"Deleted member: {name} (ID #{member_id})")
    except Exception as e:
        flash(f"Error deleting member: {e}", "danger")
    return redirect(url_for("members_list"))


@app.route("/members/<int:member_id>")
def member_profile(member_id):
    """
    Hybrid 360° Profile Page (Feature #9):
    Combines MySQL structured relational details with MongoDB workouts,
    body measurement progress, and feedback records.
    """
    # 1. SQL: Core Member Record + Joined Plan & Trainer
    member_query = """
        SELECT m.*, p.plan_name, p.duration_months, p.price AS plan_price,
               t.name AS trainer_name, t.specialization AS trainer_specialization, t.phone AS trainer_phone
        FROM members m
        LEFT JOIN plans p ON m.plan_id = p.plan_id
        LEFT JOIN trainers t ON m.trainer_id = t.trainer_id
        WHERE m.member_id = %s
    """
    member = execute_query(member_query, (member_id,), fetch_one=True)
    if not member:
        flash(f"Member #{member_id} was not found.", "danger")
        return redirect(url_for("members_list"))

    trainers_map = get_trainers_dict()

    # 2. NoSQL: MongoDB Lookups
    workout_logs = []
    progress_records = []
    feedback_records = []
    progress_chart_data = {"dates": [], "weights": [], "bodyFats": []}

    try:
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            # Workout sessions
            workout_logs = list(
                mongo_db.workout_logs.find({"member_id": member_id}).sort("date", -1)
            )

            # Fitness progress check-ins
            progress_records = list(
                mongo_db.progress.find({"member_id": member_id}).sort("date", 1)
            )

            # Chart data for weight progression
            for p in progress_records:
                progress_chart_data["dates"].append(p.get("date"))
                progress_chart_data["weights"].append(p.get("weight_kg"))
                progress_chart_data["bodyFats"].append(p.get("body_fat_pct"))

            # Trainer feedback submitted by this member
            feedback_records = list(
                mongo_db.feedback.find({"member_id": member_id}).sort("created_at", -1)
            )
            for fb in feedback_records:
                fb["trainer_name"] = trainers_map.get(fb.get("trainer_id"))
    except Exception as e:
        flash(f"Notice: Could not load NoSQL data for profile: {e}", "warning")

    return render_template(
        "members/profile.html",
        active_page="members",
        member=member,
        workout_logs=workout_logs,
        progress_records=progress_records,
        feedback_records=feedback_records,
        progress_chart_data=progress_chart_data
    )


# ==============================================================================
# 3. Trainers Management (SQL)
# ==============================================================================

@app.route("/trainers")
def trainers_list():
    """List all trainers, with assigned member count (SQL) and average rating (MongoDB)."""
    trainers = []
    try:
        query = """
            SELECT t.*, COUNT(m.member_id) AS member_count
            FROM trainers t
            LEFT JOIN members m ON t.trainer_id = m.trainer_id
            GROUP BY t.trainer_id, t.name, t.specialization, t.phone, t.created_at
            ORDER BY t.trainer_id ASC
        """
        trainers = execute_query(query) or []

        # Enhance with MongoDB average rating per trainer
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            pipeline = [
                {
                    "$group": {
                        "_id": "$trainer_id",
                        "avgRating": {"$avg": "$rating"},
                        "reviewCount": {"$sum": 1}
                    }
                }
            ]
            rating_map = {
                r["_id"]: {
                    "avg": round(r["avgRating"], 1),
                    "count": r["reviewCount"]
                }
                for r in mongo_db.feedback.aggregate(pipeline)
            }
            for t in trainers:
                r_info = rating_map.get(t["trainer_id"])
                if r_info:
                    t["avg_rating"] = r_info["avg"]
                    t["review_count"] = r_info["count"]
                else:
                    t["avg_rating"] = None
                    t["review_count"] = 0
    except Exception as e:
        flash(f"Error fetching trainers: {e}", "danger")

    return render_template("trainers/index.html", active_page="trainers", trainers=trainers)


@app.route("/trainers/add", methods=["GET", "POST"])
def trainers_add():
    """Add a new trainer with validation."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        specialization = request.form.get("specialization", "").strip()
        phone = request.form.get("phone", "").strip()

        errors = []
        if not name:
            errors.append("Trainer Name is required.")
        if not specialization:
            errors.append("Specialization is required.")
        if not phone:
            errors.append("Phone Number is required.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("trainers/form.html", active_page="trainers", is_edit=False, form_data=request.form)

        try:
            insert_query = "INSERT INTO trainers (name, specialization, phone) VALUES (%s, %s, %s)"
            new_id = execute_query(insert_query, (name, specialization, phone), commit=True)
            flash(f"Trainer '{name}' registered successfully (ID #{new_id})!", "success")
            log_activity("CREATE", "Trainers", f"Added trainer: {name} ({specialization})")
            return redirect(url_for("trainers_list"))
        except Exception as e:
            flash(f"Database error: {e}", "danger")

    return render_template("trainers/form.html", active_page="trainers", is_edit=False, form_data=None)


@app.route("/trainers/edit/<int:trainer_id>", methods=["GET", "POST"])
def trainers_edit(trainer_id):
    """Edit an existing trainer profile."""
    trainer = execute_query("SELECT * FROM trainers WHERE trainer_id = %s", (trainer_id,), fetch_one=True)
    if not trainer:
        flash(f"Trainer #{trainer_id} not found.", "danger")
        return redirect(url_for("trainers_list"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        specialization = request.form.get("specialization", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name or not specialization or not phone:
            flash("All fields are required.", "danger")
            return render_template("trainers/form.html", active_page="trainers", is_edit=True, trainer=trainer, form_data=request.form)

        try:
            update_query = "UPDATE trainers SET name = %s, specialization = %s, phone = %s WHERE trainer_id = %s"
            execute_query(update_query, (name, specialization, phone, trainer_id), commit=True)
            flash(f"Trainer #{trainer_id} ({name}) updated successfully!", "success")
            log_activity("UPDATE", "Trainers", f"Updated trainer: ID #{trainer_id} ({name})")
            return redirect(url_for("trainers_list"))
        except Exception as e:
            flash(f"Error updating trainer: {e}", "danger")

    return render_template("trainers/form.html", active_page="trainers", is_edit=True, trainer=trainer, form_data=None)


@app.route("/trainers/delete/<int:trainer_id>", methods=["POST"])
def trainers_delete(trainer_id):
    """Delete a trainer (Foreign keys use ON DELETE SET NULL)."""
    try:
        trainer = execute_query("SELECT name FROM trainers WHERE trainer_id = %s", (trainer_id,), fetch_one=True)
        name = trainer["name"] if trainer else f"ID #{trainer_id}"
        execute_query("DELETE FROM trainers WHERE trainer_id = %s", (trainer_id,), commit=True)
        flash(f"Trainer '{name}' deleted. Members assigned to this trainer have been updated.", "success")
        log_activity("DELETE", "Trainers", f"Deleted trainer: {name} (ID #{trainer_id})")
    except Exception as e:
        flash(f"Error deleting trainer: {e}", "danger")
    return redirect(url_for("trainers_list"))


# ==============================================================================
# 4. Membership Plans Management (SQL)
# ==============================================================================

@app.route("/plans")
def plans_list():
    """List plans with enrolled members count via SQL aggregate."""
    plans = []
    try:
        query = """
            SELECT p.*, COUNT(m.member_id) AS enrolled_count
            FROM plans p
            LEFT JOIN members m ON p.plan_id = m.plan_id
            GROUP BY p.plan_id, p.plan_name, p.duration_months, p.price, p.created_at
            ORDER BY p.price ASC
        """
        plans = execute_query(query) or []
    except Exception as e:
        flash(f"Error fetching membership plans: {e}", "danger")

    return render_template("plans/index.html", active_page="plans", plans=plans)


@app.route("/plans/add", methods=["GET", "POST"])
def plans_add():
    """Create a new membership plan with validation."""
    if request.method == "POST":
        plan_name = request.form.get("plan_name", "").strip()
        duration_months = request.form.get("duration_months", "").strip()
        price = request.form.get("price", "").strip()

        errors = []
        if not plan_name:
            errors.append("Plan Name is required.")
        try:
            dur = int(duration_months)
            if dur <= 0:
                errors.append("Duration must be at least 1 month.")
        except ValueError:
            errors.append("Duration must be a positive integer.")

        try:
            pr = float(price)
            if pr < 0:
                errors.append("Price cannot be negative.")
        except ValueError:
            errors.append("Price must be a valid numeric amount.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("plans/form.html", active_page="plans", is_edit=False, form_data=request.form)

        try:
            insert_query = "INSERT INTO plans (plan_name, duration_months, price) VALUES (%s, %s, %s)"
            new_id = execute_query(insert_query, (plan_name, dur, pr), commit=True)
            flash(f"Plan '{plan_name}' created successfully!", "success")
            log_activity("CREATE", "Plans", f"Created membership plan: {plan_name} (₹{pr})")
            return redirect(url_for("plans_list"))
        except Exception as e:
            flash(f"Database error: {e}", "danger")

    return render_template("plans/form.html", active_page="plans", is_edit=False, form_data=None)


@app.route("/plans/edit/<int:plan_id>", methods=["GET", "POST"])
def plans_edit(plan_id):
    """Edit membership plan details."""
    plan = execute_query("SELECT * FROM plans WHERE plan_id = %s", (plan_id,), fetch_one=True)
    if not plan:
        flash(f"Plan #{plan_id} not found.", "danger")
        return redirect(url_for("plans_list"))

    if request.method == "POST":
        plan_name = request.form.get("plan_name", "").strip()
        duration_months = request.form.get("duration_months", "").strip()
        price = request.form.get("price", "").strip()

        try:
            dur = int(duration_months)
            pr = float(price)
            if not plan_name or dur <= 0 or pr < 0:
                raise ValueError
        except ValueError:
            flash("Please enter valid plan name, positive duration, and non-negative price.", "danger")
            return render_template("plans/form.html", active_page="plans", is_edit=True, plan=plan, form_data=request.form)

        try:
            update_query = "UPDATE plans SET plan_name = %s, duration_months = %s, price = %s WHERE plan_id = %s"
            execute_query(update_query, (plan_name, dur, pr, plan_id), commit=True)
            flash(f"Plan '{plan_name}' updated successfully!", "success")
            log_activity("UPDATE", "Plans", f"Updated plan: {plan_name} (ID #{plan_id})")
            return redirect(url_for("plans_list"))
        except Exception as e:
            flash(f"Error updating plan: {e}", "danger")

    return render_template("plans/form.html", active_page="plans", is_edit=True, plan=plan, form_data=None)


@app.route("/plans/delete/<int:plan_id>", methods=["POST"])
def plans_delete(plan_id):
    """Delete a plan (Foreign keys on members use ON DELETE SET NULL)."""
    try:
        plan = execute_query("SELECT plan_name FROM plans WHERE plan_id = %s", (plan_id,), fetch_one=True)
        name = plan["plan_name"] if plan else f"ID #{plan_id}"
        execute_query("DELETE FROM plans WHERE plan_id = %s", (plan_id,), commit=True)
        flash(f"Plan '{name}' deleted.", "success")
        log_activity("DELETE", "Plans", f"Deleted membership plan: {name} (ID #{plan_id})")
    except Exception as e:
        flash(f"Error deleting plan: {e}", "danger")
    return redirect(url_for("plans_list"))


# ==============================================================================
# 5. Fitness Classes Management (SQL)
# ==============================================================================

@app.route("/classes")
def classes_list():
    """List classes joined with assigned trainers."""
    classes = []
    try:
        query = """
            SELECT c.*, t.name AS trainer_name
            FROM classes c
            LEFT JOIN trainers t ON c.trainer_id = t.trainer_id
            ORDER BY c.class_id ASC
        """
        classes = execute_query(query) or []
    except Exception as e:
        flash(f"Error fetching classes: {e}", "danger")

    return render_template("classes/index.html", active_page="classes", classes=classes)


@app.route("/classes/add", methods=["GET", "POST"])
def classes_add():
    """Schedule a new fitness class."""
    trainers = execute_query("SELECT trainer_id, name, specialization FROM trainers ORDER BY name ASC") or []

    if request.method == "POST":
        class_name = request.form.get("class_name", "").strip()
        schedule_time = request.form.get("schedule_time", "").strip()
        trainer_id = request.form.get("trainer_id") or None

        if not class_name or not schedule_time:
            flash("Class name and schedule time are required.", "danger")
            return render_template("classes/form.html", active_page="classes", is_edit=False, trainers=trainers, form_data=request.form)

        try:
            insert_query = "INSERT INTO classes (class_name, schedule_time, trainer_id) VALUES (%s, %s, %s)"
            new_id = execute_query(insert_query, (class_name, schedule_time, trainer_id), commit=True)
            flash(f"Class '{class_name}' scheduled successfully!", "success")
            log_activity("CREATE", "Classes", f"Scheduled class: {class_name} at {schedule_time}")
            return redirect(url_for("classes_list"))
        except Exception as e:
            flash(f"Error creating class: {e}", "danger")

    return render_template("classes/form.html", active_page="classes", is_edit=False, trainers=trainers, form_data=None)


@app.route("/classes/edit/<int:class_id>", methods=["GET", "POST"])
def classes_edit(class_id):
    """Edit class details."""
    gym_class = execute_query("SELECT * FROM classes WHERE class_id = %s", (class_id,), fetch_one=True)
    if not gym_class:
        flash(f"Class #{class_id} not found.", "danger")
        return redirect(url_for("classes_list"))

    trainers = execute_query("SELECT trainer_id, name, specialization FROM trainers ORDER BY name ASC") or []

    if request.method == "POST":
        class_name = request.form.get("class_name", "").strip()
        schedule_time = request.form.get("schedule_time", "").strip()
        trainer_id = request.form.get("trainer_id") or None

        if not class_name or not schedule_time:
            flash("Class name and schedule time are required.", "danger")
            return render_template("classes/form.html", active_page="classes", is_edit=True, gym_class=gym_class, trainers=trainers, form_data=request.form)

        try:
            update_query = "UPDATE classes SET class_name = %s, schedule_time = %s, trainer_id = %s WHERE class_id = %s"
            execute_query(update_query, (class_name, schedule_time, trainer_id, class_id), commit=True)
            flash(f"Class '{class_name}' updated successfully!", "success")
            log_activity("UPDATE", "Classes", f"Updated class: {class_name} (ID #{class_id})")
            return redirect(url_for("classes_list"))
        except Exception as e:
            flash(f"Error updating class: {e}", "danger")

    return render_template("classes/form.html", active_page="classes", is_edit=True, gym_class=gym_class, trainers=trainers, form_data=None)


@app.route("/classes/delete/<int:class_id>", methods=["POST"])
def classes_delete(class_id):
    """Delete a scheduled class."""
    try:
        c = execute_query("SELECT class_name FROM classes WHERE class_id = %s", (class_id,), fetch_one=True)
        name = c["class_name"] if c else f"ID #{class_id}"
        execute_query("DELETE FROM classes WHERE class_id = %s", (class_id,), commit=True)
        flash(f"Class '{name}' deleted.", "success")
        log_activity("DELETE", "Classes", f"Deleted class: {name} (ID #{class_id})")
    except Exception as e:
        flash(f"Error deleting class: {e}", "danger")
    return redirect(url_for("classes_list"))


# ==============================================================================
# 6. Workout Logs (MongoDB - Embedded Array)
# ==============================================================================

@app.route("/workouts")
def workouts_list():
    """List workout session logs from MongoDB, with optional member filter."""
    selected_member_id = request.args.get("member_id", "").strip()
    workouts = []
    members_map = get_members_dict()
    members = [{"member_id": k, "name": v} for k, v in members_map.items()]

    try:
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            filter_query = {}
            if selected_member_id:
                try:
                    filter_query["member_id"] = int(selected_member_id)
                except ValueError:
                    pass

            workouts = list(mongo_db.workout_logs.find(filter_query).sort("date", -1))
            for w in workouts:
                w["member_name"] = members_map.get(w.get("member_id"))
    except Exception as e:
        flash(f"Error querying MongoDB workout logs: {e}", "danger")

    return render_template(
        "workouts/index.html",
        active_page="workouts",
        workouts=workouts,
        members=members,
        selected_member_id=selected_member_id
    )


@app.route("/workouts/add", methods=["GET", "POST"])
def workouts_add():
    """Log a workout session containing multiple embedded exercises into MongoDB."""
    members_map = get_members_dict()
    members = [{"member_id": k, "name": v} for k, v in members_map.items()]
    preselected_member_id = request.args.get("member_id", "")

    if request.method == "POST":
        member_id_str = request.form.get("member_id")
        workout_date = request.form.get("date", "").strip()
        notes = request.form.get("notes", "").strip()

        # Extract dynamic exercise lists
        exercise_names = request.form.getlist("exercise_name[]")
        sets_list = request.form.getlist("sets[]")
        reps_list = request.form.getlist("reps[]")
        weight_list = request.form.getlist("weight[]")

        errors = []
        if not member_id_str:
            errors.append("Member selection is required.")
        if not workout_date:
            errors.append("Workout date is required.")

        exercises = []
        for i in range(len(exercise_names)):
            ename = exercise_names[i].strip()
            if not ename:
                continue
            try:
                s = int(sets_list[i]) if i < len(sets_list) else 3
                r = int(reps_list[i]) if i < len(reps_list) else 10
                w = float(weight_list[i]) if i < len(weight_list) else 0.0
                exercises.append({"name": ename, "sets": s, "reps": r, "weight": w})
            except (ValueError, IndexError):
                pass

        if not exercises:
            errors.append("You must include at least one valid exercise.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                "workouts/form.html",
                active_page="workouts",
                members=members,
                preselected_member_id=member_id_str
            )

        try:
            mongo_db = get_mongo_db()
            if mongo_db is None:
                raise ConnectionError("MongoDB is offline.")

            doc = {
                "member_id": int(member_id_str),
                "date": workout_date,
                "exercises": exercises,
                "notes": notes,
                "created_at": datetime.now()
            }
            mongo_db.workout_logs.insert_one(doc)
            member_name = members_map.get(int(member_id_str), f"ID #{member_id_str}")
            flash(f"Workout logged successfully for {member_name} ({len(exercises)} exercises)!", "success")
            log_activity("CREATE", "Workouts", f"Logged workout for {member_name} on {workout_date} ({len(exercises)} exercises)")
            return redirect(url_for("workouts_list", member_id=member_id_str))
        except Exception as e:
            flash(f"Failed to record workout to MongoDB: {e}", "danger")

    return render_template(
        "workouts/form.html",
        active_page="workouts",
        members=members,
        preselected_member_id=preselected_member_id
    )


@app.route("/workouts/delete/<string:log_id>", methods=["POST"])
def workouts_delete(log_id):
    """Delete a workout log document by its MongoDB ObjectId."""
    try:
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            mongo_db.workout_logs.delete_one({"_id": ObjectId(log_id)})
            flash("Workout session log deleted.", "success")
            log_activity("DELETE", "Workouts", f"Deleted workout log ID: {log_id}")
    except Exception as e:
        flash(f"Error deleting workout log: {e}", "danger")

    return_url = request.form.get("return_url") or url_for("workouts_list")
    return redirect(return_url)


# ==============================================================================
# 7. Progress Tracker (MongoDB - Sub-documents & Chart.js)
# ==============================================================================

@app.route("/progress")
def progress_list():
    """List progress records and render Chart.js line graph of weight over time."""
    selected_member_id = request.args.get("member_id", "").strip()
    progress_records = []
    members_map = get_members_dict()
    members = [{"member_id": k, "name": v} for k, v in members_map.items()]
    selected_member = None

    chart_data = {"dates": [], "weights": [], "bodyFats": []}

    try:
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            filter_query = {}
            if selected_member_id:
                try:
                    m_id_int = int(selected_member_id)
                    filter_query["member_id"] = m_id_int
                    selected_member = {"member_id": m_id_int, "name": members_map.get(m_id_int, f"Member #{m_id_int}")}
                except ValueError:
                    pass

            progress_records = list(mongo_db.progress.find(filter_query).sort("date", 1))
            for p in progress_records:
                p["member_name"] = members_map.get(p.get("member_id"))
                chart_data["dates"].append(p.get("date"))
                chart_data["weights"].append(p.get("weight_kg"))
                chart_data["bodyFats"].append(p.get("body_fat_pct"))
    except Exception as e:
        flash(f"Error loading progress from MongoDB: {e}", "danger")

    return render_template(
        "progress/index.html",
        active_page="progress",
        progress_records=list(reversed(progress_records)),
        chart_data=chart_data,
        members=members,
        selected_member_id=selected_member_id,
        selected_member=selected_member
    )


@app.route("/progress/add", methods=["GET", "POST"])
def progress_add():
    """Add a body composition measurement check-in into MongoDB."""
    members_map = get_members_dict()
    members = [{"member_id": k, "name": v} for k, v in members_map.items()]
    preselected_member_id = request.args.get("member_id", "")

    if request.method == "POST":
        member_id_str = request.form.get("member_id")
        check_date = request.form.get("date", "").strip()
        weight_str = request.form.get("weight_kg", "").strip()
        body_fat_str = request.form.get("body_fat_pct", "").strip()
        chest_str = request.form.get("chest", "").strip()
        waist_str = request.form.get("waist", "").strip()
        arms_str = request.form.get("arms", "").strip()

        errors = []
        if not member_id_str:
            errors.append("Member selection is required.")
        if not check_date:
            errors.append("Date is required.")
        try:
            weight = float(weight_str)
            if weight <= 0:
                errors.append("Weight must be positive.")
        except ValueError:
            errors.append("Weight must be a valid number.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("progress/form.html", active_page="progress", members=members, preselected_member_id=member_id_str)

        try:
            body_fat = float(body_fat_str) if body_fat_str else None
            measurements = {
                "chest": float(chest_str) if chest_str else None,
                "waist": float(waist_str) if waist_str else None,
                "arms": float(arms_str) if arms_str else None
            }

            doc = {
                "member_id": int(member_id_str),
                "date": check_date,
                "weight_kg": weight,
                "body_fat_pct": body_fat,
                "measurements": measurements,
                "created_at": datetime.now()
            }

            mongo_db = get_mongo_db()
            if mongo_db is None:
                raise ConnectionError("MongoDB is offline.")

            mongo_db.progress.insert_one(doc)
            member_name = members_map.get(int(member_id_str), f"ID #{member_id_str}")
            flash(f"Progress check-in logged for {member_name} ({weight} kg)!", "success")
            log_activity("CREATE", "Progress", f"Logged progress for {member_name}: {weight}kg on {check_date}")
            return redirect(url_for("progress_list", member_id=member_id_str))
        except Exception as e:
            flash(f"Failed to record progress: {e}", "danger")

    return render_template(
        "progress/form.html",
        active_page="progress",
        members=members,
        preselected_member_id=preselected_member_id
    )


@app.route("/progress/delete/<string:progress_id>", methods=["POST"])
def progress_delete(progress_id):
    """Delete a progress record from MongoDB."""
    try:
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            mongo_db.progress.delete_one({"_id": ObjectId(progress_id)})
            flash("Progress check-in deleted.", "success")
            log_activity("DELETE", "Progress", f"Deleted progress record ID: {progress_id}")
    except Exception as e:
        flash(f"Error deleting progress record: {e}", "danger")
    return redirect(url_for("progress_list"))


# ==============================================================================
# 8. Feedback (MongoDB - Trainer Reviews & Aggregations)
# ==============================================================================

@app.route("/feedback")
def feedback_list():
    """List feedback reviews with trainer rating aggregations."""
    feedback_entries = []
    trainer_summaries = []
    members_map = get_members_dict()
    trainers_map = get_trainers_dict()

    try:
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            feedback_entries = list(mongo_db.feedback.find().sort("created_at", -1))
            for fb in feedback_entries:
                fb["member_name"] = members_map.get(fb.get("member_id"))
                fb["trainer_name"] = trainers_map.get(fb.get("trainer_id"))

            # Trainer rating summary cards via aggregation
            pipeline = [
                {
                    "$group": {
                        "_id": "$trainer_id",
                        "avgRating": {"$avg": "$rating"},
                        "totalReviews": {"$sum": 1}
                    }
                },
                {"$sort": {"avgRating": -1}}
            ]
            for r in mongo_db.feedback.aggregate(pipeline):
                t_id = r["_id"]
                trainer_summaries.append({
                    "trainer_id": t_id,
                    "trainer_name": trainers_map.get(t_id, f"Trainer #{t_id}"),
                    "avg_rating": round(r["avgRating"], 1),
                    "total_reviews": r["totalReviews"]
                })
    except Exception as e:
        flash(f"Error loading feedback: {e}", "danger")

    return render_template(
        "feedback/index.html",
        active_page="feedback",
        feedback_list=feedback_entries,
        trainer_summaries=trainer_summaries
    )


@app.route("/feedback/add", methods=["GET", "POST"])
def feedback_add():
    """Submit a rating and review for a gym trainer."""
    members_map = get_members_dict()
    trainers_map = get_trainers_dict()
    members = [{"member_id": k, "name": v} for k, v in members_map.items()]
    trainers = [{"trainer_id": k, "name": v} for k, v in trainers_map.items()]
    preselected_member_id = request.args.get("member_id", "")

    if request.method == "POST":
        member_id = request.form.get("member_id")
        trainer_id = request.form.get("trainer_id")
        rating_str = request.form.get("rating")
        comment = request.form.get("comment", "").strip()

        errors = []
        if not member_id or not trainer_id or not rating_str or not comment:
            errors.append("All fields are required to submit a review.")
        try:
            rating = int(rating_str)
            if not (1 <= rating <= 5):
                errors.append("Rating must be between 1 and 5 stars.")
        except ValueError:
            errors.append("Invalid rating value.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                "feedback/form.html",
                active_page="feedback",
                members=members,
                trainers=trainers,
                preselected_member_id=member_id
            )

        try:
            mongo_db = get_mongo_db()
            if mongo_db is None:
                raise ConnectionError("MongoDB is offline.")

            doc = {
                "member_id": int(member_id),
                "trainer_id": int(trainer_id),
                "rating": rating,
                "comment": comment,
                "created_at": datetime.now()
            }
            mongo_db.feedback.insert_one(doc)
            trainer_name = trainers_map.get(int(trainer_id), f"ID #{trainer_id}")
            flash(f"Feedback submitted successfully for {trainer_name} ({rating}★)!", "success")
            log_activity("CREATE", "Feedback", f"Member #{member_id} rated trainer #{trainer_id} ({rating} stars)")
            return redirect(url_for("feedback_list"))
        except Exception as e:
            flash(f"Error saving feedback: {e}", "danger")

    return render_template(
        "feedback/form.html",
        active_page="feedback",
        members=members,
        trainers=trainers,
        preselected_member_id=preselected_member_id
    )


@app.route("/feedback/delete/<string:feedback_id>", methods=["POST"])
def feedback_delete(feedback_id):
    """Delete a feedback entry from MongoDB."""
    try:
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            mongo_db.feedback.delete_one({"_id": ObjectId(feedback_id)})
            flash("Review deleted successfully.", "success")
            log_activity("DELETE", "Feedback", f"Deleted feedback record: {feedback_id}")
    except Exception as e:
        flash(f"Error deleting feedback: {e}", "danger")
    return redirect(url_for("feedback_list"))


# ==============================================================================
# 9. Reports Page (SQL Joins + Group By + Hybrid Analytics)
# ==============================================================================

@app.route("/reports")
def reports():
    """
    DBMS Analytical Reports (Feature #9):
    1. SQL JOIN: Comprehensive Member + Plan + Trainer
    2. SQL COUNT + GROUP BY: Member distribution & total revenue per plan
    3. Hybrid Synthesis: Trainer workload (SQL) vs Rating Performance (MongoDB)
    """
    join_report = []
    group_report = []
    trainer_performance = []

    # 1. SQL Reports
    try:
        # Multi-table JOIN
        join_query = """
            SELECT m.member_id, m.name, m.email, m.phone, m.join_date,
                   p.plan_name, p.price,
                   t.name AS trainer_name, t.specialization
            FROM members m
            LEFT JOIN plans p ON m.plan_id = p.plan_id
            LEFT JOIN trainers t ON m.trainer_id = t.trainer_id
            ORDER BY m.member_id ASC
        """
        join_report = execute_query(join_query) or []

        # GROUP BY + Aggregate (Members per plan & total revenue)
        group_query = """
            SELECT p.plan_id, p.plan_name, p.duration_months, p.price,
                   COUNT(m.member_id) AS total_enrolled,
                   (COUNT(m.member_id) * p.price) AS total_revenue
            FROM plans p
            LEFT JOIN members m ON p.plan_id = m.plan_id
            GROUP BY p.plan_id, p.plan_name, p.duration_months, p.price
            ORDER BY total_enrolled DESC
        """
        group_report = execute_query(group_query) or []

        # Trainer performance SQL core
        tp_sql_query = """
            SELECT t.trainer_id, t.name, t.specialization,
                   COUNT(DISTINCT m.member_id) AS assigned_members,
                   COUNT(DISTINCT c.class_id) AS classes_count
            FROM trainers t
            LEFT JOIN members m ON t.trainer_id = m.trainer_id
            LEFT JOIN classes c ON t.trainer_id = c.trainer_id
            GROUP BY t.trainer_id, t.name, t.specialization
            ORDER BY assigned_members DESC
        """
        trainer_performance = execute_query(tp_sql_query) or []

        # Enhance Trainer Performance with MongoDB ratings
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            pipeline = [
                {
                    "$group": {
                        "_id": "$trainer_id",
                        "avgRating": {"$avg": "$rating"},
                        "reviewCount": {"$sum": 1}
                    }
                }
            ]
            rating_lookup = {
                r["_id"]: (round(r["avgRating"], 1), r["reviewCount"])
                for r in mongo_db.feedback.aggregate(pipeline)
            }
            for tp in trainer_performance:
                t_id = tp["trainer_id"]
                if t_id in rating_lookup:
                    tp["avg_rating"] = rating_lookup[t_id][0]
                    tp["review_count"] = rating_lookup[t_id][1]
                else:
                    tp["avg_rating"] = None
                    tp["review_count"] = 0
    except Exception as e:
        flash(f"Error compiling reports: {e}", "danger")

    return render_template(
        "reports/index.html",
        active_page="reports",
        join_report=join_report,
        group_report=group_report,
        trainer_performance=trainer_performance
    )


# ==============================================================================
# 10. Activity Logs (MongoDB - Audit Trail)
# ==============================================================================

@app.route("/activity-logs")
def activity_logs():
    """List recent MongoDB activity logs with optional module filter."""
    selected_module = request.args.get("module", "").strip()
    logs = []
    try:
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            filter_query = {}
            if selected_module:
                filter_query["module"] = selected_module
            logs = list(mongo_db.activity_logs.find(filter_query).sort("timestamp", -1).limit(100))
    except Exception as e:
        flash(f"Error loading activity logs: {e}", "danger")

    return render_template(
        "activity_logs/index.html",
        active_page="activity_logs",
        logs=logs,
        selected_module=selected_module
    )


# ==============================================================================
# Application Entry Point
# ==============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print(" FitTrack - Gym Management System (Flask Server)")
    print(" Running at: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
