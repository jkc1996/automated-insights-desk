import sqlite3
import os
import random

db_dir = os.path.dirname(__file__)
db_path = os.path.join(db_dir, "dummy_data.db")


def setup_fat_database():

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # -------------------------
    # DROP OLD TABLES
    # -------------------------

    cursor.execute("DROP TABLE IF EXISTS sales_transactions")
    cursor.execute("DROP TABLE IF EXISTS customer_activity")
    cursor.execute("DROP TABLE IF EXISTS customers")
    cursor.execute("DROP TABLE IF EXISTS regional_sales")
    cursor.execute("DROP TABLE IF EXISTS company_metrics")

    # -------------------------
    # COMPANY METRICS
    # -------------------------

    cursor.execute("""
    CREATE TABLE company_metrics (
        id INTEGER PRIMARY KEY,
        month TEXT,
        revenue REAL,
        active_users INTEGER,
        subscription_tier TEXT
    )
    """)

    # -------------------------
    # REGIONAL SALES
    # -------------------------

    cursor.execute("""
    CREATE TABLE regional_sales (
        id INTEGER PRIMARY KEY,
        region TEXT,
        sales_amount REAL,
        month_id INTEGER,
        FOREIGN KEY(month_id) REFERENCES company_metrics(id)
    )
    """)

    # -------------------------
    # CUSTOMERS
    # -------------------------

    cursor.execute("""
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        company_name TEXT,
        region TEXT,
        subscription_tier TEXT,
        signup_month TEXT
    )
    """)

    # -------------------------
    # CUSTOMER ACTIVITY
    # -------------------------

    cursor.execute("""
    CREATE TABLE customer_activity (
        activity_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        month TEXT,
        logins INTEGER,
        feature_usage INTEGER,
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
    )
    """)

    # -------------------------
    # SALES TRANSACTIONS (NEW)
    # -------------------------

    cursor.execute("""
    CREATE TABLE sales_transactions (
        transaction_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        month_id INTEGER,
        amount REAL,
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY(month_id) REFERENCES company_metrics(id)
    )
    """)

    # -------------------------
    # COMPANY METRICS DATA
    # -------------------------

    months = [
        "January 2025","February 2025","March 2025","April 2025","May 2025","June 2025",
        "July 2025","August 2025","September 2025","October 2025","November 2025","December 2025",
        "January 2026","February 2026","March 2026"
    ]

    tiers = ["Enterprise", "Pro"]

    metrics_rows = []
    idx = 1

    base_revenue = {
        "Enterprise": 40000,
        "Pro": 15000
    }

    for month_index, month in enumerate(months):

        for tier in tiers:

            revenue = base_revenue[tier] + month_index * 3000
            users = 1000 + month_index * 120

            metrics_rows.append((idx, month, revenue, users, tier))
            idx += 1

    cursor.executemany(
        "INSERT INTO company_metrics VALUES (?,?,?,?,?)",
        metrics_rows
    )

    # -------------------------
    # REGIONAL SALES
    # -------------------------

    regions = ["North America", "Europe", "APAC", "South America"]

    regional_rows = []
    rid = 1

    for metric in metrics_rows:

        month_id = metric[0]
        revenue = metric[2]

        regional_rows.append((rid, "North America", revenue * 0.40, month_id)); rid += 1
        regional_rows.append((rid, "Europe", revenue * 0.30, month_id)); rid += 1
        regional_rows.append((rid, "APAC", revenue * 0.20, month_id)); rid += 1
        regional_rows.append((rid, "South America", revenue * 0.10, month_id)); rid += 1

    cursor.executemany(
        "INSERT INTO regional_sales VALUES (?,?,?,?)",
        regional_rows
    )

    # -------------------------
    # CUSTOMERS
    # -------------------------

    companies = [
        "TechNova","CloudNest","ApexAI","BlueCore","Skylytics",
        "NextGen Labs","BrightMetrics","DataForge","InnovaWorks",
        "QuantumSoft","Orbit Systems","StratusAI","HeliosData",
        "Vector Analytics","Nimbus Tech","Atlas Cloud"
    ]

    regions = ["North America", "Europe", "APAC", "South America"]

    customers = []

    for i in range(1, 101):

        name = companies[i % len(companies)] + f" Ltd {i}"
        region = regions[i % 4]
        tier = "Enterprise" if i % 3 == 0 else "Pro"
        signup = months[i % len(months)]

        customers.append((i, name, region, tier, signup))

    cursor.executemany(
        "INSERT INTO customers VALUES (?,?,?,?,?)",
        customers
    )

    # -------------------------
    # CUSTOMER ACTIVITY
    # -------------------------

    activity = []
    aid = 1

    for customer_id in range(1, 101):

        for m in months[-6:]:

            logins = 20 + (customer_id % 10) * 5
            usage = 10 + (customer_id % 8) * 3

            activity.append((aid, customer_id, m, logins, usage))
            aid += 1

    cursor.executemany(
        "INSERT INTO customer_activity VALUES (?,?,?,?,?)",
        activity
    )

    # -------------------------
    # SALES TRANSACTIONS DATA
    # -------------------------

    transactions = []
    tid = 1

    for customer_id in range(1, 101):

        for metric in metrics_rows:

            month_id = metric[0]

            # simulate subscription payments
            amount = random.randint(800, 3000)

            transactions.append(
                (tid, customer_id, month_id, amount)
            )

            tid += 1

    cursor.executemany(
        "INSERT INTO sales_transactions VALUES (?,?,?,?)",
        transactions
    )

    conn.commit()
    conn.close()

    print("✅ Realistic analytics database created")
    print("Tables:")
    print(" - company_metrics")
    print(" - regional_sales")
    print(" - customers")
    print(" - customer_activity")
    print(" - sales_transactions (NEW)")


if __name__ == "__main__":
    setup_fat_database()
    