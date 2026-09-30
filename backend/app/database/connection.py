"""MySQL Database connection and query helper module.

Provides connection management and query execution using mysql-connector-python.
Loads credentials dynamically from environment variables.
"""
import os
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error, pooling

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "fraud_detection_db")


def get_db_config(include_database: bool = True) -> Dict[str, Any]:
    """Return database connection parameters from environment."""
    config: Dict[str, Any] = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "autocommit": True,
    }
    if include_database and DB_NAME:
        config["database"] = DB_NAME
    return config


def get_raw_connection(include_database: bool = True):
    """Create a raw MySQL connection."""
    config = get_db_config(include_database=include_database)
    return mysql.connector.connect(**config)


@contextmanager
def get_connection(include_database: bool = True) -> Generator[Any, None, None]:
    """Context manager for obtaining a database connection."""
    conn = get_raw_connection(include_database=include_database)
    try:
        yield conn
    finally:
        if conn.is_connected():
            conn.close()


@contextmanager
def get_cursor(
    dictionary: bool = True, include_database: bool = True
) -> Generator[Any, None, None]:
    """Context manager for obtaining a database cursor."""
    with get_connection(include_database=include_database) as conn:
        cursor = conn.cursor(dictionary=dictionary)
        try:
            yield cursor
        finally:
            cursor.close()


def check_connection() -> bool:
    """Check if connection to MySQL database is successful."""
    try:
        with get_connection(include_database=True) as conn:
            return conn.is_connected()
    except Error:
        return False


def get_customer_history(
    customer_id: str, limit: int = 100
) -> List[Dict[str, Any]]:
    """Retrieve historical transactions for a given customer ordered by timestamp descending.

    Args:
        customer_id: Customer identifier (e.g. 'C101').
        limit: Maximum number of transactions to return (default: 100).

    Returns:
        List of transaction records as dictionaries.
    """
    query = """
        SELECT
            transaction_id,
            customer_id,
            CAST(amount AS DOUBLE) AS amount,
            timestamp,
            CAST(latitude AS DOUBLE) AS latitude,
            CAST(longitude AS DOUBLE) AS longitude,
            location_name,
            merchant,
            transaction_type,
            channel,
            created_at
        FROM transactions
        WHERE customer_id = %s
        ORDER BY timestamp DESC
        LIMIT %s;
    """
    try:
        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, (customer_id, limit))
            records = cursor.fetchall()
            return records
    except Error as e:
        print(f"[Database Error] Failed to fetch customer history for {customer_id}: {e}")
        return []
