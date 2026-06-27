import sqlite3
from werkzeug.security import generate_password_hash

# This is the file name we are using now
DB_NAME = 'home_health_db.db'

def create_fresh_user(username, password, role):
    conn = None
    try:
        # We connect directly to the FILE, not a server
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        
        # Hash the password for security
        hashed_password = generate_password_hash(password)
        
        # SQLite uses '?' as placeholders
        cur.execute("""
            INSERT INTO users (username, password_hash, role) 
            VALUES (?, ?, ?)
        """, (username, hashed_password, role))
        
        conn.commit()
        print(f"--- SUCCESS: User '{username}' created in {DB_NAME} ---")
        
    except sqlite3.OperationalError:
        print("--- ERROR: Table 'users' not found. Run init_db.py first! ---")
    except sqlite3.IntegrityError:
        print(f"--- ERROR: User '{username}' already exists. ---")
    except Exception as e:
        print(f"--- ERROR: {e} ---")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_fresh_user('Joy', 'joy123', 'Staff')