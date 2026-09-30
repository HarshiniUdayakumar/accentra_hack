"""Synthetic historical transaction data generator and seeder for MySQL.

Generates ~500 realistic historical transactions across 20 customers (C101 to C120)
with distinct behavioral profiles, locations, spending ranges, and realistic intervals.

Usage:
    python scripts/seed_history.py [--clear]
"""
import argparse
from datetime import datetime, timedelta
import os
import random
import sys
from typing import Any, Dict, List, Tuple

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

# Indian Cities with realistic coordinates and local merchants
CITIES: Dict[str, Dict[str, Any]] = {
    "Chennai": {
        "lat": 13.0827,
        "lon": 80.2707,
        "merchants": [
            "Saravana Stores T Nagar",
            "Express Avenue Mall",
            "Swiggy Chennai",
            "Zomato Chennai",
            "Uber Chennai",
            "Apollo Pharmacy Adyar",
            "Shell Fuel OMR",
            "Nilgiris Supermarket",
            "Woodlands Cafe Mylapore",
        ],
    },
    "Bangalore": {
        "lat": 12.9716,
        "lon": 77.5946,
        "merchants": [
            "Indiranagar Cafe",
            "BigBasket Bangalore",
            "Swiggy Bangalore",
            "Zomato Bangalore",
            "Uber Bangalore",
            "Decathlon Koramangala",
            "Croma Whitefield",
            "Shell Fuel Electronic City",
            "Corner House Ice Cream",
        ],
    },
    "Hyderabad": {
        "lat": 17.3850,
        "lon": 78.4867,
        "merchants": [
            "Paradise Biryani Secunderabad",
            "Inorbit Mall Hitech City",
            "Swiggy Hyderabad",
            "Apollo Hospitals Jubilee Hills",
            "Uber Hyderabad",
            "Ratnadeep Supermarket Banjara Hills",
            "GVK One Mall",
        ],
    },
    "Mumbai": {
        "lat": 19.0760,
        "lon": 72.8777,
        "merchants": [
            "Nature's Basket Bandra",
            "Phoenix Palladium Lower Parel",
            "Swiggy Mumbai",
            "Zomato Mumbai",
            "Uber Mumbai",
            "Reliance Smart Point Andheri",
            "Cafe Mondegar Colaba",
        ],
    },
    "Delhi": {
        "lat": 28.6139,
        "lon": 77.2090,
        "merchants": [
            "Select Citywalk Saket",
            "Khan Market Gourmet",
            "Swiggy Delhi",
            "Zomato Delhi",
            "Uber Delhi",
            "Modern Bazaar CP",
            "DLF CyberHub Gurugram",
        ],
    },
    "Coimbatore": {
        "lat": 11.0168,
        "lon": 76.9558,
        "merchants": [
            "Brookefields Mall",
            "Sree Annapoorna RS Puram",
            "Swiggy Coimbatore",
            "Coimbatore Departmental Stores",
            "Uber Coimbatore",
            "Ganga Hospital Pharmacy",
        ],
    },
}

TRANSACTION_TYPES = ["PAYMENT", "TRANSFER", "PURCHASE", "REFUND_CREDIT", "SUBSCRIPTION"]
CHANNELS = ["UPI", "POS", "MOBILE_APP", "NET_BANKING", "DEBIT_CARD", "CREDIT_CARD"]

# Specific Customer Profiles (20 customers, generating ~500 transactions)
CUSTOMER_PROFILES: List[Dict[str, Any]] = [
    # C101: Mostly Chennai, small frequent amounts (₹300 - ₹2,000), frequent transactions
    {
        "customer_id": "C101",
        "txn_count": 35,
        "cities": [("Chennai", 0.92), ("Bangalore", 0.08)],
        "amount_range": (300.0, 2000.0),
        "spike_amount_prob": 0.05,
        "spike_multiplier": (1.5, 2.2),
        "primary_channels": ["UPI", "POS", "MOBILE_APP"],
    },
    # C102: Chennai + Bangalore business traveler, moderate amounts (₹1,000 - ₹5,000)
    {
        "customer_id": "C102",
        "txn_count": 30,
        "cities": [("Chennai", 0.55), ("Bangalore", 0.38), ("Mumbai", 0.07)],
        "amount_range": (1000.0, 5000.0),
        "spike_amount_prob": 0.10,
        "spike_multiplier": (2.0, 3.5),
        "primary_channels": ["CREDIT_CARD", "NET_BANKING", "UPI"],
    },
    # C103: Mostly Chennai, lower frequency, amounts ₹500 - ₹3,000
    {
        "customer_id": "C103",
        "txn_count": 16,
        "cities": [("Chennai", 0.90), ("Coimbatore", 0.10)],
        "amount_range": (500.0, 3000.0),
        "spike_amount_prob": 0.04,
        "spike_multiplier": (1.4, 2.0),
        "primary_channels": ["DEBIT_CARD", "UPI"],
    },
    # C104: Bangalore tech worker, amounts ₹800 - ₹4,500, visits Hyderabad/Chennai
    {
        "customer_id": "C104",
        "txn_count": 28,
        "cities": [("Bangalore", 0.78), ("Hyderabad", 0.14), ("Chennai", 0.08)],
        "amount_range": (800.0, 4500.0),
        "spike_amount_prob": 0.08,
        "spike_multiplier": (2.5, 4.0),
        "primary_channels": ["UPI", "CREDIT_CARD", "MOBILE_APP"],
    },
    # C105: Mumbai student/micro-spends, high frequency ₹50 - ₹800
    {
        "customer_id": "C105",
        "txn_count": 38,
        "cities": [("Mumbai", 0.96), ("Delhi", 0.04)],
        "amount_range": (50.0, 800.0),
        "spike_amount_prob": 0.03,
        "spike_multiplier": (1.8, 2.5),
        "primary_channels": ["UPI", "POS"],
    },
    # C106: Delhi consultant, amounts ₹1,200 - ₹6,000, travels to Mumbai
    {
        "customer_id": "C106",
        "txn_count": 25,
        "cities": [("Delhi", 0.75), ("Mumbai", 0.25)],
        "amount_range": (1200.0, 6000.0),
        "spike_amount_prob": 0.08,
        "spike_multiplier": (1.8, 2.8),
        "primary_channels": ["CREDIT_CARD", "NET_BANKING"],
    },
    # C107: Hyderabad healthcare doctor, amounts ₹1,500 - ₹7,000
    {
        "customer_id": "C107",
        "txn_count": 24,
        "cities": [("Hyderabad", 0.88), ("Bangalore", 0.12)],
        "amount_range": (1500.0, 7000.0),
        "spike_amount_prob": 0.06,
        "spike_multiplier": (1.6, 2.4),
        "primary_channels": ["CREDIT_CARD", "POS", "UPI"],
    },
    # C108: Coimbatore textile business, amounts ₹2,000 - ₹9,000, visits Chennai
    {
        "customer_id": "C108",
        "txn_count": 22,
        "cities": [("Coimbatore", 0.70), ("Chennai", 0.30)],
        "amount_range": (2000.0, 9000.0),
        "spike_amount_prob": 0.12,
        "spike_multiplier": (2.2, 3.2),
        "primary_channels": ["NET_BANKING", "CREDIT_CARD"],
    },
    # C109: Chennai freelancer, ₹400 - ₹2,500
    {
        "customer_id": "C109",
        "txn_count": 26,
        "cities": [("Chennai", 0.92), ("Bangalore", 0.08)],
        "amount_range": (400.0, 2500.0),
        "spike_amount_prob": 0.04,
        "spike_multiplier": (1.5, 2.0),
        "primary_channels": ["UPI", "MOBILE_APP"],
    },
    # C110: Bangalore product manager, ₹1,000 - ₹4,000
    {
        "customer_id": "C110",
        "txn_count": 25,
        "cities": [("Bangalore", 0.84), ("Mumbai", 0.16)],
        "amount_range": (1000.0, 4000.0),
        "spike_amount_prob": 0.06,
        "spike_multiplier": (1.7, 2.5),
        "primary_channels": ["CREDIT_CARD", "UPI"],
    },
    # C111: Mumbai creative agency, ₹1,500 - ₹8,000
    {
        "customer_id": "C111",
        "txn_count": 24,
        "cities": [("Mumbai", 0.80), ("Delhi", 0.20)],
        "amount_range": (1500.0, 8000.0),
        "spike_amount_prob": 0.08,
        "spike_multiplier": (2.0, 3.0),
        "primary_channels": ["CREDIT_CARD", "NET_BANKING"],
    },
    # C112: Delhi professor, ₹600 - ₹3,500
    {
        "customer_id": "C112",
        "txn_count": 20,
        "cities": [("Delhi", 0.90), ("Chennai", 0.10)],
        "amount_range": (600.0, 3500.0),
        "spike_amount_prob": 0.05,
        "spike_multiplier": (1.5, 2.0),
        "primary_channels": ["DEBIT_CARD", "NET_BANKING"],
    },
    # C113: Hyderabad engineer, ₹900 - ₹4,200
    {
        "customer_id": "C113",
        "txn_count": 25,
        "cities": [("Hyderabad", 0.84), ("Bangalore", 0.16)],
        "amount_range": (900.0, 4200.0),
        "spike_amount_prob": 0.06,
        "spike_multiplier": (1.8, 2.6),
        "primary_channels": ["UPI", "POS"],
    },
    # C114: Coimbatore senior, ₹300 - ₹1,800
    {
        "customer_id": "C114",
        "txn_count": 18,
        "cities": [("Coimbatore", 0.94), ("Chennai", 0.06)],
        "amount_range": (300.0, 1800.0),
        "spike_amount_prob": 0.03,
        "spike_multiplier": (1.4, 1.8),
        "primary_channels": ["DEBIT_CARD", "POS"],
    },
    # C115: Chennai backend dev, ₹500 - ₹2,800
    {
        "customer_id": "C115",
        "txn_count": 27,
        "cities": [("Chennai", 0.88), ("Bangalore", 0.12)],
        "amount_range": (500.0, 2800.0),
        "spike_amount_prob": 0.05,
        "spike_multiplier": (1.6, 2.2),
        "primary_channels": ["UPI", "MOBILE_APP"],
    },
    # C116: Bangalore founder, multi-city traveler, ₹2,000 - ₹10,000
    {
        "customer_id": "C116",
        "txn_count": 28,
        "cities": [("Bangalore", 0.60), ("Mumbai", 0.25), ("Delhi", 0.15)],
        "amount_range": (2000.0, 10000.0),
        "spike_amount_prob": 0.10,
        "spike_multiplier": (2.0, 3.5),
        "primary_channels": ["CREDIT_CARD", "NET_BANKING"],
    },
    # C117: Mumbai investor, ₹1,000 - ₹5,500
    {
        "customer_id": "C117",
        "txn_count": 22,
        "cities": [("Mumbai", 0.90), ("Hyderabad", 0.10)],
        "amount_range": (1000.0, 5500.0),
        "spike_amount_prob": 0.06,
        "spike_multiplier": (1.8, 2.5),
        "primary_channels": ["CREDIT_CARD", "UPI"],
    },
    # C118: Delhi merchant, ₹1,500 - ₹6,500
    {
        "customer_id": "C118",
        "txn_count": 26,
        "cities": [("Delhi", 0.85), ("Mumbai", 0.15)],
        "amount_range": (1500.0, 6500.0),
        "spike_amount_prob": 0.07,
        "spike_multiplier": (1.9, 2.8),
        "primary_channels": ["POS", "UPI", "NET_BANKING"],
    },
    # C119: Hyderabad product marketer, ₹800 - ₹3,800
    {
        "customer_id": "C119",
        "txn_count": 23,
        "cities": [("Hyderabad", 0.85), ("Chennai", 0.15)],
        "amount_range": (800.0, 3800.0),
        "spike_amount_prob": 0.05,
        "spike_multiplier": (1.7, 2.4),
        "primary_channels": ["UPI", "POS"],
    },
    # C120: Coimbatore logistics, ₹1,200 - ₹5,000
    {
        "customer_id": "C120",
        "txn_count": 26,
        "cities": [("Coimbatore", 0.75), ("Chennai", 0.25)],
        "amount_range": (1200.0, 5000.0),
        "spike_amount_prob": 0.08,
        "spike_multiplier": (1.8, 2.6),
        "primary_channels": ["NET_BANKING", "DEBIT_CARD"],
    },
]


def pick_weighted_city(city_weights: List[Tuple[str, float]], rng: random.Random) -> str:
    """Choose city according to customer profile distribution."""
    cities, weights = zip(*city_weights)
    return rng.choices(cities, weights=weights, k=1)[0]


def generate_synthetic_transactions(seed: int = 42) -> List[Dict[str, Any]]:
    """Generate deterministic synthetic historical transactions."""
    rng = random.Random(seed)
    transactions: List[Dict[str, Any]] = []

    # Generate transactions spread over the last 14 days, ending 10 minutes ago
    base_time = datetime.now().replace(microsecond=0) - timedelta(minutes=10)

    for profile in CUSTOMER_PROFILES:
        cid = profile["customer_id"]
        count = profile["txn_count"]
        city_weights = profile["cities"]
        min_amt, max_amt = profile["amount_range"]
        spike_prob = profile["spike_amount_prob"]
        spike_min, spike_max = profile["spike_multiplier"]
        channels = profile["primary_channels"]

        # Generate timestamps backwards or chronologically over 14 days
        # We distribute 'count' points across 14 days with realistic variations
        total_seconds = 14 * 24 * 3600
        # Sample sorted offsets
        offsets = sorted([rng.randint(600, total_seconds) for _ in range(count)], reverse=True)

        for i, offset in enumerate(offsets, start=1):
            txn_id = f"TXN_{cid}_{i:03d}"
            txn_time = base_time - timedelta(seconds=offset)

            # Location selection
            city_name = pick_weighted_city(city_weights, rng)
            city_info = CITIES[city_name]

            # Realistic micro jitter within city bounds (±0.008 deg ~ 800m)
            lat = round(city_info["lat"] + rng.uniform(-0.008, 0.008), 6)
            lon = round(city_info["lon"] + rng.uniform(-0.008, 0.008), 6)
            merchant = rng.choice(city_info["merchants"])

            # Amount calculation
            base_amount = rng.uniform(min_amt, max_amt)
            if rng.random() < spike_prob:
                # Occasional legitimate spike
                base_amount *= rng.uniform(spike_min, spike_max)
            amount = round(base_amount, 2)

            channel = rng.choice(channels)
            txn_type = "PURCHASE" if channel in ["POS", "DEBIT_CARD", "CREDIT_CARD"] else "PAYMENT"

            transactions.append(
                {
                    "transaction_id": txn_id,
                    "customer_id": cid,
                    "amount": amount,
                    "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "latitude": lat,
                    "longitude": lon,
                    "location_name": city_name,
                    "merchant": merchant,
                    "transaction_type": txn_type,
                    "channel": channel,
                }
            )

    return transactions


def seed_database(clear_existing: bool = False) -> Tuple[bool, int]:
    """Insert generated transactions into MySQL transactions table."""
    transactions = generate_synthetic_transactions()
    total_txns = len(transactions)
    print(f"Generated {total_txns} deterministic synthetic transactions across {len(CUSTOMER_PROFILES)} customers.")

    insert_query = """
        INSERT INTO transactions (
            transaction_id,
            customer_id,
            amount,
            timestamp,
            latitude,
            longitude,
            location_name,
            merchant,
            transaction_type,
            channel
        ) VALUES (
            %(transaction_id)s,
            %(customer_id)s,
            %(amount)s,
            %(timestamp)s,
            %(latitude)s,
            %(longitude)s,
            %(location_name)s,
            %(merchant)s,
            %(transaction_type)s,
            %(channel)s
        )
        ON DUPLICATE KEY UPDATE
            amount = VALUES(amount),
            timestamp = VALUES(timestamp),
            latitude = VALUES(latitude),
            longitude = VALUES(longitude),
            location_name = VALUES(location_name),
            merchant = VALUES(merchant),
            transaction_type = VALUES(transaction_type),
            channel = VALUES(channel);
    """

    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            autocommit=False,
        )
        cursor = conn.cursor()

        if clear_existing:
            print("Clearing existing transaction records...")
            cursor.execute("TRUNCATE TABLE transactions;")
            conn.commit()

        print(f"Inserting/updating {total_txns} records into 'transactions' table...")
        cursor.executemany(insert_query, transactions)
        conn.commit()

        # Count records in table
        cursor.execute("SELECT COUNT(*) FROM transactions;")
        row_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        print(f"Successfully seeded database! Total rows in 'transactions' table: {row_count}")
        return True, row_count

    except Error as e:
        print(f"Database error during seeding: {e}", file=sys.stderr)
        return False, 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic transaction history.")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing transactions table before seeding.",
    )
    args = parser.parse_args()

    success, count = seed_database(clear_existing=args.clear)
    sys.exit(0 if success else 1)
