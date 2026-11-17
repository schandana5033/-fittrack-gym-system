"""
FitTrack Gym Management System - Application Configuration
===========================================================
DBMS Architecture Note:
This configuration file manages the parameters for Polyglot Persistence:
1. MySQL (Relational / RDBMS): Handles ACID-compliant structured business entities
   (Members, Trainers, Membership Plans, and Fitness Classes).
2. MongoDB (Document / NoSQL): Handles schema-free, variable, and high-velocity
   data (Workout logs with dynamic exercise lists, body measurements, reviews, audit trails).
"""

import os
from pathlib import Path

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# Attempt to load .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

class Config:
    """Base application configuration class."""
    
    # Flask Security & Session Management
    SECRET_KEY = os.getenv("SECRET_KEY", "fittrack-secure-secret-key-dbms-project-2026")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "t")

    # -------------------------------------------------------------------------
    # MySQL Database Configuration (RDBMS)
    # -------------------------------------------------------------------------
    # Primary data store for entities requiring strict schema, ACID transactions,
    # uniqueness constraints (e.g. member email), and foreign key integrity.
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB = os.getenv("MYSQL_DB", "fittrack_db")
    MYSQL_CONNECT_TIMEOUT = int(os.getenv("MYSQL_CONNECT_TIMEOUT", 5))

    # -------------------------------------------------------------------------
    # MongoDB Database Configuration (NoSQL)
    # -------------------------------------------------------------------------
    # Document database storing nested JSON-like documents (BSON) where exercise lists
    # and metric types vary wildly per user or workout style.
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB = os.getenv("MONGO_DB", "fittrack_nosql")
    MONGO_SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", 2500))
