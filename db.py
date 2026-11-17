"""
FitTrack Gym Management System - Database Layer (db.py)
=======================================================
DBMS CONCEPT EXPLANATION FOR VIVA:
----------------------------------
This module implements the 'Polyglot Persistence' pattern:
Using different data storage technologies (SQL + NoSQL) for what each does best:

1. RDBMS (MySQL):
   - Strict Schema: Member identity, financial plans, contractual trainer assignments.
   - ACID Properties: Atomicity, Consistency, Isolation, Durability.
   - SQL Injection Prevention: Uses PARAMETERIZED QUERIES with '%s' placeholders.
     Values are passed separately as tuples to the database engine driver,
     ensuring input data is never evaluated as SQL syntax.
   - Cursor: Uses `pymysql.cursors.DictCursor` so records return as dictionaries
     (e.g., row['name'] instead of row[1]), making it easy to integrate with templates.

2. Document Store (MongoDB):
   - Flexible / Dynamic Schema: Workout logs where one member does 3 sets of bench press,
     while another records 5 sets of squats plus cardio intervals.
   - Hierarchical Embedding: Exercise lists embedded directly inside workout documents
     rather than requiring a separate junction table.
   - Time-series Fitness Progress: Measurement metrics (weight, body fat, chest, waist, arms)
     which can evolve over time without ALTER TABLE migrations.
   - High-throughput Activity Auditing: Centralized logging of all application events.
"""

import logging
from datetime import datetime
import pymysql
import pymysql.cursors
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fittrack.db")

# Cached MongoDB client instance
_mongo_client = None

# ==============================================================================
# MySQL Database Connection Helper
# ==============================================================================

def get_mysql_connection():
    """
    Establishes and returns a connection to MySQL using PyMySQL.
    Returns:
        pymysql.Connection or None if connection fails.
    """
    try:
        connection = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=Config.MYSQL_CONNECT_TIMEOUT,
            autocommit=True
        )
        return connection
    except Exception as e:
        logger.error(f"[MySQL Connection Error]: {e}")
        return None


def execute_query(query, params=None, fetch_one=False, fetch_all=True, commit=False):
    """
    Executes a parameterized SQL query safely against MySQL.
    
    SECURITY NOTE (SQL INJECTION PREVENTION):
    - Query uses '%s' parameter markers.
    - User input is supplied strictly via the 'params' argument.
    - The database driver automatically escapes and quotes parameters.
    """
    conn = get_mysql_connection()
    if conn is None:
        raise ConnectionError("Unable to establish connection to MySQL server.")
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            
            if commit:
                conn.commit()
                return cursor.lastrowid
            
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            return cursor.rowcount
    finally:
        conn.close()


# ==============================================================================
# MongoDB Connection Helper
# ==============================================================================

def get_mongo_client():
    """
    Initializes or returns an existing PyMongo MongoClient instance.
    Uses short serverSelectionTimeoutMS to prevent thread hangs when Mongo is down.
    """
    global _mongo_client
    if _mongo_client is None:
        try:
            _mongo_client = MongoClient(
                Config.MONGO_URI,
                serverSelectionTimeoutMS=Config.MONGO_SERVER_SELECTION_TIMEOUT_MS
            )
        except Exception as e:
            logger.error(f"[MongoDB Client Init Error]: {e}")
            return None
    return _mongo_client


def get_mongo_db():
    """
    Returns the MongoDB database instance for 'fittrack_nosql'.
    Returns None if MongoDB is unreachable.
    """
    client = get_mongo_client()
    if client is None:
        return None
    try:
        # Quick server ping to confirm connectivity
        client.admin.command('ping')
        return client[Config.MONGO_DB]
    except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
        logger.warning(f"[MongoDB Ping Warning]: MongoDB unreachable: {e}")
        return None


# ==============================================================================
# MongoDB Auto-Logging (activity_logs collection)
# ==============================================================================

def log_activity(action, module, details):
    """
    Auto-logs administrative and member actions to MongoDB collection: 'activity_logs'.
    Schema:
    {
        "action": str,       # 'CREATE', 'UPDATE', 'DELETE', 'VIEW'
        "module": str,       # 'Members', 'Trainers', 'Plans', 'Classes', 'Workouts', etc.
        "timestamp": datetime,
        "details": str
    }
    Gracefully handles MongoDB offline status without interrupting main request.
    """
    try:
        db = get_mongo_db()
        if db is not None:
            db.activity_logs.insert_one({
                "action": action.upper(),
                "module": module,
                "timestamp": datetime.now(),
                "details": str(details)
            })
        else:
            logger.info(f"[Activity Log (Fallback)] {action} in {module}: {details}")
    except Exception as e:
        logger.error(f"[Failed to log activity to MongoDB]: {e}")


# ==============================================================================
# Health Diagnostics
# ==============================================================================

def check_db_health():
    """
    Checks the status of both MySQL and MongoDB connections.
    Returns:
        dict: {'mysql': bool, 'mongo': bool, 'mysql_msg': str, 'mongo_msg': str}
    """
    health = {
        "mysql": False,
        "mongo": False,
        "mysql_msg": "Not Connected",
        "mongo_msg": "Not Connected"
    }

    # Test MySQL
    try:
        conn = get_mysql_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 AS alive")
                res = cursor.fetchone()
                if res and res.get('alive') == 1:
                    health["mysql"] = True
                    health["mysql_msg"] = f"Connected ({Config.MYSQL_DB}@{Config.MYSQL_HOST}:{Config.MYSQL_PORT})"
            conn.close()
    except Exception as e:
        health["mysql_msg"] = str(e)

    # Test MongoDB
    try:
        db = get_mongo_db()
        if db is not None:
            health["mongo"] = True
            health["mongo_msg"] = f"Connected ({Config.MONGO_DB})"
    except Exception as e:
        health["mongo_msg"] = str(e)

    return health
