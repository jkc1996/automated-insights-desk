import sqlite3
import os

# Ensure the data directory exists
db_dir = os.path.dirname(__file__)
db_path = os.path.join(db_dir, 'dummy_data.db')

def setup_fat_database():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Monthly Revenue & User Growth
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_metrics (
            id INTEGER PRIMARY KEY,
            month TEXT,
            revenue REAL,
            active_users INTEGER,
            subscription_tier TEXT
        )
    ''')

    # 2. Regional Breakdown (For more complex joins)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regional_sales (
            id INTEGER PRIMARY KEY,
            region TEXT,
            sales_amount REAL,
            month_id INTEGER,
            FOREIGN KEY(month_id) REFERENCES company_metrics(id)
        )
    ''')

    # --- POULATING DATA ---

    # Core Metrics
    metrics_data = [
        (1, 'January 2026', 45000.0, 1200, 'Enterprise'),
        (2, 'January 2026', 15000.0, 4500, 'Pro'),
        (3, 'February 2026', 52000.0, 1350, 'Enterprise'),
        (4, 'February 2026', 18500.0, 5100, 'Pro'),
        (5, 'March 2026', 61000.0, 1600, 'Enterprise'),
        (6, 'March 2026', 22000.0, 5800, 'Pro')
    ]

    # Regional Data
    regional_data = [
        ('North America', 25000.0, 1),
        ('Europe', 15000.0, 1),
        ('APAC', 5000.0, 1),
        ('North America', 28000.0, 3),
        ('Europe', 18000.0, 3),
        ('APAC', 6000.0, 3),
        ('North America', 35000.0, 5),
        ('Europe', 20000.0, 5),
        ('APAC', 6000.0, 5)
    ]

    cursor.executemany('INSERT OR REPLACE INTO company_metrics VALUES (?,?,?,?,?)', metrics_data)
    cursor.executemany('INSERT OR REPLACE INTO regional_sales (region, sales_amount, month_id) VALUES (?,?,?)', regional_data)

    conn.commit()
    conn.close()
    print(f"✅ 'Fat' Database created at {db_path}")
    print("📊 Ready for Forensic Analysis!")

if __name__ == "__main__":
    setup_fat_database()
    