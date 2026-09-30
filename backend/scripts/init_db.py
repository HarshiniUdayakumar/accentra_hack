"""Database initialization script.

Creates the MySQL database and the transactions table if they do not already exist.
Usage:
    python scripts/init_db.py
"""
import os
import sys

# Ensure backend root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv(os.path.join(BACKEND_DIR, ".env"))

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "fraud_detection_db")

TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id      VARCHAR(50) PRIMARY KEY,
    customer_id         VARCHAR(50) NOT NULL,
    amount              DECIMAL(12,2) NOT NULL,
    timestamp           DATETIME NOT NULL,
    latitude            DECIMAL(10,6),
    longitude           DECIMAL(10,6),
    location_name       VARCHAR(100),
    merchant            VARCHAR(100),
    transaction_type    VARCHAR(50),
    channel             VARCHAR(50),
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_customer_timestamp (customer_id, timestamp DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def init_database() -> bool:
    """Connect to MySQL, create database and transactions table."""
    print(f"Connecting to MySQL at {DB_HOST}:{DB_PORT} as user '{DB_USER}'...")
    try:
        # Step 1: Connect to server without database to ensure database exists
        server_conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            autocommit=True,
        )
        server_cursor = server_conn.cursor()
        print(f"Creating database '{DB_NAME}' if not exists...")
        server_cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        server_cursor.close()
        server_conn.close()

        # Step 2: Connect to the specific database
        db_conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            autocommit=True,
        )
        db_cursor = db_conn.cursor()
        print(f"Creating table 'transactions' in database '{DB_NAME}'...")
        db_cursor.execute(TABLE_SCHEMA)
        db_cursor.close()
        db_conn.close()

        print(f"Database '{DB_NAME}' and table 'transactions' initialized successfully!")
        return True

    except Error as e:
        print(f"Database initialization error: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
