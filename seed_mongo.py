"""
FitTrack Gym Management System - MongoDB Seed Script
===================================================
DBMS CONCEPT EXPLANATION FOR VIVA:
----------------------------------
This script initializes and seeds the NoSQL Document Database ('fittrack_nosql').
Unlike SQL's fixed tabular schema, MongoDB stores flexible JSON-like BSON documents.

Collections Seeded:
1. 'workout_logs': Demonstrates EMBEDDED ARRAYS. Each workout session contains an array
   of exercise documents [{name, sets, reps, weight}], capturing complex hierarchies
   in a single document without requiring foreign key joins.
2. 'progress': Demonstrates EMBEDDED SUB-DOCUMENTS. Measurements are nested {chest, waist, arms},
   providing natural grouping of related physical attributes over time.
3. 'feedback': Captures member ratings and reviews linked via 'member_id' and 'trainer_id'.
4. 'activity_logs': Real-time audit trail of actions taken across the system.
"""

from datetime import datetime, timedelta
from pymongo import MongoClient
from config import Config

def seed_mongodb():
    print("=" * 60)
    print(" FitTrack Gym Management System - MongoDB Seeder")
    print("=" * 60)
    print(f"Connecting to MongoDB at: {Config.MONGO_URI} ...")

    try:
        client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=3000)
        # Verify connection
        client.admin.command('ping')
        db = client[Config.MONGO_DB]
        print(f"✓ Connected to database: '{Config.MONGO_DB}'")
    except Exception as e:
        print(f"✗ ERROR: Unable to connect to MongoDB server.\n  Details: {e}")
        print("\nPlease ensure the MongoDB service (mongod) is running.")
        return False

    # 1. Clear existing collections
    print("\n[1/5] Resetting collections in 'fittrack_nosql'...")
    db.workout_logs.drop()
    db.progress.drop()
    db.feedback.drop()
    db.activity_logs.drop()
    print("✓ Old collections dropped.")

    # 2. Seed Workout Logs
    print("\n[2/5] Seeding 'workout_logs' (demonstrates embedded exercise arrays)...")
    workouts = [
        {
            "member_id": 1,  # Rahul Sharma
            "date": "2026-03-01",
            "exercises": [
                {"name": "Barbell Bench Press", "sets": 4, "reps": 10, "weight": 65.0},
                {"name": "Incline Dumbbell Flyes", "sets": 3, "reps": 12, "weight": 16.0},
                {"name": "Tricep Rope Pushdowns", "sets": 3, "reps": 15, "weight": 25.0}
            ],
            "notes": "Great chest and tricep pump. Target weight achieved cleanly.",
            "created_at": datetime.now() - timedelta(days=15)
        },
        {
            "member_id": 1,
            "date": "2026-03-05",
            "exercises": [
                {"name": "Barbell Squats", "sets": 5, "reps": 8, "weight": 85.0},
                {"name": "Romanian Deadlifts", "sets": 4, "reps": 10, "weight": 70.0},
                {"name": "Leg Press Machine", "sets": 3, "reps": 12, "weight": 150.0}
            ],
            "notes": "Heavy leg day. Completed all reps with full depth.",
            "created_at": datetime.now() - timedelta(days=11)
        },
        {
            "member_id": 2,  # Ananya Sen
            "date": "2026-03-02",
            "exercises": [
                {"name": "Surya Namaskar (Sun Salutations)", "sets": 6, "reps": 1, "weight": 0.0},
                {"name": "Warrior Flow Sequence", "sets": 3, "reps": 1, "weight": 0.0},
                {"name": "Core Navasana (Boat Pose)", "sets": 4, "reps": 30, "weight": 0.0}
            ],
            "notes": "Focused on breath pacing and thoracic spine mobility.",
            "created_at": datetime.now() - timedelta(days=14)
        },
        {
            "member_id": 3,  # Rohan Mehta
            "date": "2026-03-04",
            "exercises": [
                {"name": "Kettlebell Swings", "sets": 4, "reps": 20, "weight": 24.0},
                {"name": "Plyometric Box Jumps", "sets": 4, "reps": 15, "weight": 0.0},
                {"name": "Battle Ropes Waves", "sets": 5, "reps": 30, "weight": 0.0}
            ],
            "notes": "High heart-rate CrossFit conditioning session.",
            "created_at": datetime.now() - timedelta(days=12)
        },
        {
            "member_id": 4,  # Sneha Patel
            "date": "2026-03-08",
            "exercises": [
                {"name": "Conventional Deadlifts", "sets": 4, "reps": 6, "weight": 95.0},
                {"name": "Wide Grip Lat Pulldowns", "sets": 4, "reps": 10, "weight": 45.0},
                {"name": "Seated Cable Rows", "sets": 3, "reps": 12, "weight": 40.0}
            ],
            "notes": "Upper back power day. Form was solid on heavy pulls.",
            "created_at": datetime.now() - timedelta(days=8)
        }
    ]
    db.workout_logs.insert_many(workouts)
    print(f"✓ Inserted {len(workouts)} workout log documents.")

    # 3. Seed Fitness Progress Records
    print("\n[3/5] Seeding 'progress' (demonstrates embedded metric documents & time series)...")
    progress_records = [
        # Rahul Sharma Progress History
        {
            "member_id": 1,
            "date": "2026-01-10",
            "weight_kg": 82.5,
            "body_fat_pct": 22.4,
            "measurements": {"chest": 40.0, "waist": 34.5, "arms": 13.5},
            "created_at": datetime(2026, 1, 10)
        },
        {
            "member_id": 1,
            "date": "2026-02-10",
            "weight_kg": 80.2,
            "body_fat_pct": 20.8,
            "measurements": {"chest": 40.5, "waist": 33.2, "arms": 14.0},
            "created_at": datetime(2026, 2, 10)
        },
        {
            "member_id": 1,
            "date": "2026-03-10",
            "weight_kg": 78.0,
            "body_fat_pct": 19.1,
            "measurements": {"chest": 41.0, "waist": 32.0, "arms": 14.5},
            "created_at": datetime(2026, 3, 10)
        },
        # Ananya Sen Progress History
        {
            "member_id": 2,
            "date": "2026-02-01",
            "weight_kg": 62.0,
            "body_fat_pct": 25.0,
            "measurements": {"chest": 34.0, "waist": 28.5, "arms": 10.5},
            "created_at": datetime(2026, 2, 1)
        },
        {
            "member_id": 2,
            "date": "2026-03-01",
            "weight_kg": 60.5,
            "body_fat_pct": 23.8,
            "measurements": {"chest": 34.0, "waist": 27.5, "arms": 11.0},
            "created_at": datetime(2026, 3, 1)
        },
        # Rohan Mehta Progress History
        {
            "member_id": 3,
            "date": "2026-02-15",
            "weight_kg": 76.0,
            "body_fat_pct": 18.0,
            "measurements": {"chest": 38.0, "waist": 31.0, "arms": 13.0},
            "created_at": datetime(2026, 2, 15)
        },
        {
            "member_id": 3,
            "date": "2026-03-15",
            "weight_kg": 74.5,
            "body_fat_pct": 16.5,
            "measurements": {"chest": 39.0, "waist": 30.0, "arms": 13.8},
            "created_at": datetime(2026, 3, 15)
        }
    ]
    db.progress.insert_many(progress_records)
    print(f"✓ Inserted {len(progress_records)} progress check-in documents.")

    # 4. Seed Trainer Feedback
    print("\n[4/5] Seeding 'feedback' (demonstrates reviews linked across DBs)...")
    feedback_entries = [
        {
            "member_id": 1,
            "trainer_id": 1,  # Arjun Verma
            "rating": 5,
            "comment": "Arjun is a phenomenal coach. His strength progression plan increased my bench press significantly!",
            "created_at": datetime(2026, 2, 20, 14, 30)
        },
        {
            "member_id": 2,
            "trainer_id": 2,  # Priya Nair
            "rating": 5,
            "comment": "Priya's yoga sessions have relieved my chronic lower back stiffness. Very patient and knowledgeable instructor.",
            "created_at": datetime(2026, 2, 25, 11, 15)
        },
        {
            "member_id": 3,
            "trainer_id": 3,  # Vikram Singh
            "rating": 4,
            "comment": "Vikram pushes you to your absolute limits in CrossFit. Intense sessions, excellent stamina building.",
            "created_at": datetime(2026, 3, 2, 18, 45)
        },
        {
            "member_id": 4,
            "trainer_id": 1,  # Arjun Verma
            "rating": 5,
            "comment": "Superb attention to lifting biomechanics and injury prevention. Highly recommended!",
            "created_at": datetime(2026, 3, 10, 16, 20)
        },
        {
            "member_id": 5,
            "trainer_id": 4,  # Sarah Khan
            "rating": 4,
            "comment": "Sarah keeps cardio sessions high energy and fun. Never a boring minute in class.",
            "created_at": datetime(2026, 3, 12, 19, 0)
        }
    ]
    db.feedback.insert_many(feedback_entries)
    print(f"✓ Inserted {len(feedback_entries)} trainer feedback documents.")

    # 5. Seed Activity Logs
    print("\n[5/5] Seeding 'activity_logs' (demonstrates audit trail collection)...")
    activities = [
        {
            "action": "CREATE",
            "module": "System",
            "timestamp": datetime.now() - timedelta(days=20),
            "details": "Initialized FitTrack Relational & Document database schemas."
        },
        {
            "action": "CREATE",
            "module": "Members",
            "timestamp": datetime.now() - timedelta(days=15),
            "details": "Registered new member: Rahul Sharma (Plan: Monthly Basic, Trainer: Arjun Verma)."
        },
        {
            "action": "CREATE",
            "module": "Workouts",
            "timestamp": datetime.now() - timedelta(days=11),
            "details": "Logged workout session for Member ID 1 (3 exercises)."
        },
        {
            "action": "CREATE",
            "module": "Progress",
            "timestamp": datetime.now() - timedelta(days=6),
            "details": "Logged body composition measurement for Member ID 1 (Weight: 78.0 kg)."
        },
        {
            "action": "CREATE",
            "module": "Feedback",
            "timestamp": datetime.now() - timedelta(days=4),
            "details": "Member ID 4 submitted 5-star rating for Trainer ID 1."
        }
    ]
    db.activity_logs.insert_many(activities)
    print(f"✓ Inserted {len(activities)} activity audit documents.")

    print("\n" + "=" * 60)
    print(" MongoDB seeding completed successfully!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    seed_mongodb()
