import sqlite3

def patch_database():
    # Ensure this matches your DB_NAME in init_db.py
    conn = sqlite3.connect('home_health_db.db')
    cursor = conn.cursor()

    print("Checking for missing clinical workflow columns...")

    # Comprehensive list of columns required for the Staff Dashboard features
    columns_to_ensure = [
        "clinical_status TEXT DEFAULT 'Monitoring'",
        "lab_results TEXT",
        "test_interpretation TEXT",
        "treatment_plan TEXT",
        "pharmacy_notes TEXT",
        "symptoms TEXT",
        "last_diagnosis_summary TEXT",
        "clinical_decision TEXT",
        "decision_justification TEXT"
    ]

    for col_def in columns_to_ensure:
        col_name = col_def.split()[0]
        try:
            cursor.execute(f"ALTER TABLE patients ADD COLUMN {col_def}")
            print(f"✅ Added: {col_name}")
        except sqlite3.OperationalError:
            # This happens if the column already exists
            print(f"ℹ️ Already exists: {col_name}")

    # Ensure the appointments table has the department column (Fixes Billing Error)
    try:
        cursor.execute("ALTER TABLE appointments ADD COLUMN department TEXT DEFAULT 'General Practice'")
        print("✅ Added: department to appointments table")
    except sqlite3.OperationalError:
        print("ℹ️ Already exists: department in appointments table")

    conn.commit()
    conn.close()
    print("\n🚀 Database is now fully compatible with the Clinical Workflow!")

if __name__ == "__main__":
    patch_database()