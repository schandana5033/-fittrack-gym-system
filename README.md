# FitTrack - Gym Management System
### A Complete Hybrid SQL + NoSQL DBMS Web Application

FitTrack is a production-ready gym management system built to demonstrate **Polyglot Persistence** in database management systems (DBMS). It seamlessly pairs a relational database (**MySQL**) for core transactional business data with a document database (**MongoDB**) for flexible, variable, and high-velocity workout logs and body metrics.

---

## 🌐 Local Website Access Link

When running, access the web application in your browser at:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)** or **[http://localhost:5000](http://localhost:5000)**

---

## 🏗️ Architecture & Database Design

FitTrack uses **Polyglot Persistence**—choosing the optimal database engine for each specific data requirement:

```
                            ┌──────────────────────────────────────────┐
                            │        FitTrack Flask Application         │
                            │           (http://127.0.0.1:5000)        │
                            └────────────────────┬─────────────────────┘
                                                 │
                     ┌───────────────────────────┴───────────────────────────┐
                     ▼                                                       ▼
        ┌─────────────────────────┐                             ┌─────────────────────────┐
        │      MySQL (RDBMS)      │                             │     MongoDB (NoSQL)     │
        │      fittrack_db        │                             │     fittrack_nosql      │
        ├─────────────────────────┤                             ├─────────────────────────┤
        │ • plans                 │                             │ • workout_logs          │
        │ • trainers              │ ◄─── Linked via member_id ──► • progress              │
        │ • members               │       and trainer_id        │ • feedback              │
        │ • classes               │                             │ • activity_logs         │
        └─────────────────────────┘                             └─────────────────────────┘
```

### 1. SQL Database (MySQL - `fittrack_db`)
- **`plans`**: `(plan_id PK, plan_name, duration_months, price, created_at)`
- **`trainers`**: `(trainer_id PK, name, specialization, phone, created_at)`
- **`members`**: `(member_id PK, name, email UNIQUE, phone, join_date, plan_id FK, trainer_id FK, created_at)`
  - Foreign keys configured with `ON DELETE SET NULL` and `ON UPDATE CASCADE`.
- **`classes`**: `(class_id PK, class_name, schedule_time, trainer_id FK, created_at)`
- **Security**: All SQL interactions use **Parameterized Queries** (`%s` placeholders) via PyMySQL to prevent SQL Injection vulnerabilities.

### 2. NoSQL Database (MongoDB - `fittrack_nosql`)
- **`workout_logs`**: Embedded array schema `{ member_id, date, exercises: [{ name, sets, reps, weight }], notes }`
- **`progress`**: Embedded sub-document schema `{ member_id, date, weight_kg, body_fat_pct, measurements: { chest, waist, arms } }`
- **`feedback`**: Member reviews `{ member_id, trainer_id, rating (1-5), comment, created_at }`
- **`activity_logs`**: High-velocity audit trail `{ action, module, timestamp, details }`

---

## 🚀 Quick Setup & Installation

### Step 1: Clone or Navigate to Project Directory
```powershell
cd C:\Users\HP\.gemini\antigravity\scratch\fittrack-gym-system
```

### Step 2: Install Python Dependencies
Ensure you have Python 3.10+ installed:
```powershell
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Open `.env` in any text editor and adjust your MySQL credentials:
```ini
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=fittrack_db

MONGO_URI=mongodb://localhost:27017/
MONGO_DB=fittrack_nosql
```

### Step 4: Initialize MySQL Database
Run `schema.sql` into your MySQL instance using Command Prompt or MySQL Workbench:
```powershell
mysql -u root -p < schema.sql
```
*(This creates `fittrack_db`, defines all tables with constraints, and inserts sample data for members, trainers, plans, and classes).*

### Step 5: Start MongoDB & Seed Sample NoSQL Data
Ensure your local MongoDB daemon is running (`mongod`), then execute:
```powershell
python seed_mongo.py
```
*(This seeds initial workout logs, progress measurements, feedback reviews, and audit logs).*

### Step 6: Start the Web Server
```powershell
python app.py
```
You will see:
```
============================================================
 FitTrack - Gym Management System (Flask Server)
 Running at: http://127.0.0.1:5000
============================================================
```

Now open **http://127.0.0.1:5000** in your browser!

---

## 🌟 Key Application Features

1. **Executive Dashboard**:
   - Total Members, Trainers, Plans, Classes (calculated using SQL `COUNT(*)`)
   - Total Workout Sessions logged & Average Trainer Rating (calculated using MongoDB `$group` aggregation pipeline)
   - Real-time DB status indicators (MySQL & MongoDB connectivity health pills)
2. **Members Management (CRUD)**:
   - Full CRUD with parameterized queries
   - Server-side email format validation and duplicate email verification
   - Interactive search and filter
3. **Trainers & Classes**:
   - Manage instructors, assignments, and class schedules with relational `JOIN`s
4. **Membership Plans**:
   - Manage duration tiers, pricing, and view real-time enrolled member counts
5. **Workout Logging (MongoDB)**:
   - Dynamic JavaScript interface to add/remove exercise sets on the fly
   - Embedded exercise arrays saved directly to BSON documents
6. **Progress Tracker & Chart.js**:
   - Track weight, body fat %, and circumference measurements (chest, waist, arms)
   - Interactive Chart.js line graph of weight trends over time
7. **Trainer Feedback**:
   - Member ratings (1-5 stars) and reviews
   - Aggregation cards showing average score per trainer
8. **DBMS Analytical Reports**:
   - **Report 1 (SQL JOIN)**: Multi-table relational query combining Member + Plan + Trainer
   - **Report 2 (SQL GROUP BY)**: Member distribution per plan and projected revenue generated
   - **Report 3 (Hybrid Performance)**: Relational assigned member counts combined with MongoDB ratings
9. **Hybrid 360° Member Profile**:
   - Unites relational SQL identity with NoSQL workout logs, progress charts, and feedback reviews
10. **MongoDB Activity Audit Trail**:
    - Automatically logs every create, update, and delete action across all modules

---

## 🎓 DBMS Viva / Exam Q&A Reference

### Q1: Why use both SQL and NoSQL instead of just one?
**Answer:** This pattern is called **Polyglot Persistence**. 
- **MySQL (SQL)** provides ACID transactions, rigid schemas, and strict referential integrity (foreign keys) which are critical for financial plans, trainer assignments, and membership accounts.
- **MongoDB (NoSQL)** provides schema flexibility and hierarchical data storage. A workout session contains a variable list of exercises with different reps/weights that fit naturally into an embedded array without complex junction tables. Similarly, activity logs benefit from MongoDB's fast append-only document ingestion.

### Q2: How does the application prevent SQL Injection?
**Answer:** The application strictly uses **parameterized queries** with `%s` placeholders via PyMySQL. Values are never concatenated into the query string; instead, they are sent as separate parameters to the database driver, which automatically escapes and formats them safely.

### Q3: How are SQL and NoSQL data linked together?
**Answer:** The primary key of the MySQL table (`members.member_id` and `trainers.trainer_id`) is stored as an integer attribute in the MongoDB documents (`workout_logs.member_id`, `progress.member_id`, `feedback.trainer_id`). The application layer joins them in memory when rendering views such as the **Member 360° Profile**.

### Q4: What happens if a Trainer is deleted?
**Answer:** Because the foreign key constraint is configured with `ON DELETE SET NULL`:
```sql
CONSTRAINT fk_members_trainer FOREIGN KEY (trainer_id) REFERENCES trainers(trainer_id) ON DELETE SET NULL
```
Deleting a trainer will safely set the `trainer_id` of all assigned members to `NULL`, preserving member accounts without violating referential integrity.
