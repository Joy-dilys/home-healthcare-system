import sqlite3
from werkzeug.security import generate_password_hash

# Define the database file name
DB_NAME = 'home_health_db.db'

def init_sqlite_db():
    # Establish a single connection for the entire process
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print("Creating tables...")

    # 1. Patients Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_info TEXT,
            staff_id INTEGER DEFAULT 1,
            is_active TINYINT DEFAULT 1,
            lifeline_status TINYINT DEFAULT 0,
            heart_rate_min INT DEFAULT 50,
            heart_rate_max INT DEFAULT 100,
            bp_systolic_max INT DEFAULT 140,
            bp_diastolic_max INT DEFAULT 90,
            glucose_max DECIMAL(5,2) DEFAULT 180.00,
            clinical_status TEXT DEFAULT 'Monitoring', 
            symptoms TEXT,
            lab_results TEXT,
            test_interpretation TEXT,
            treatment_plan TEXT,
            pharmacy_notes TEXT,
            last_diagnosis_summary TEXT,
            clinical_decision TEXT,
            decision_justification TEXT
        );
    """)

    # 2. Healthdata Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS healthdata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            heart_rate INTEGER,
            bp_systolic INTEGER,
            bp_diastolic INTEGER,
            glucose DECIMAL(5, 2),
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        );
    """)

    # 3. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Staff'
        );
    """)

    # 4. Alerts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            alert_type TEXT,
            message TEXT,
            is_resolved TINYINT DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        );
    """)

    # 5. Notifications Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT NOT NULL,
            link TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER DEFAULT 0
        );
    """)

    # 6. Appointments Table (Includes Department column now)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            appt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor_user_id INTEGER,
            appt_time DATETIME,
            department TEXT DEFAULT 'General Practice',
            status TEXT DEFAULT 'Pending'
        );
    """)

    # 7. Department Rates Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS department_rates (
            dept_id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_name TEXT UNIQUE,
            base_fee REAL
        )
    """)

    # 8. Billing Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS billing (
            bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
            appt_id INTEGER,
            patient_id INTEGER,
            amount REAL,
            payment_status TEXT DEFAULT 'Unpaid',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (appt_id) REFERENCES appointments (appt_id),
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        )
    """)

    print("Inserting initial data and department rates...")

    # Pre-fill department rates
    rates = [
        ('General Practice', 50.00),
        ('Cardiology', 150.00),
        ('Endocrinology', 120.00),
        ('Laboratory', 80.00)
    ]
    cursor.executemany("INSERT OR IGNORE INTO department_rates (department_name, base_fee) VALUES (?, ?)", rates)

    # Initial Admin User
    hashed_pw = generate_password_hash('password123')
    cursor.execute("""
        INSERT OR IGNORE INTO users (id, username, password_hash, role) 
        VALUES (1, 'admin', ?, 'Admin')
    """, (hashed_pw,))

    # Test Patient
    cursor.execute("""
        INSERT OR IGNORE INTO patients (patient_id, name, contact_info, staff_id, is_active, clinical_status) 
        VALUES (1, 'Test Patient', '+254700000000', 1, 1, 'Monitoring')
    """)

    conn.commit()
    conn.close()
    print(f"✅ Database '{DB_NAME}' fully initialized and seeded successfully.")

if __name__ == "__main__":
    init_sqlite_db()