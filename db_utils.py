import sys

def fetch_unresolved_alerts(cursor, staff_id):
    """Fetches all unresolved alerts for the staff member using SQLite syntax."""
    try:
        query = """
            SELECT
                a.alert_id, a.alert_type, a.timestamp, p.patient_id, p.name, a.message
            FROM alerts a 
            JOIN patients p ON a.patient_id = p.patient_id 
            WHERE a.is_resolved = 0 
            AND p.staff_id = ? 
            ORDER BY a.timestamp DESC
        """
        # Changed %s to ? for SQLite compatibility
        cursor.execute(query, (staff_id,))
        return cursor.fetchall()
    except Exception as e:
        print(f"Error in fetch_unresolved_alerts: {e}", file=sys.stderr)
        return []

def fetch_all_active_patients(cursor):
    """Fetches key information for all active patients."""
    try:
        # SQLite queries without parameters stay exactly the same
        query = "SELECT patient_id, name, contact_info, lifeline_status, heart_rate_min, heart_rate_max, bp_sys_max, bp_dia_max, glucose_max FROM patients WHERE is_active = 1"
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error in fetch_all_active_patients: {e}", file=sys.stderr)
        return []

def fetch_unread_notifications(cursor, staff_id):
    """Fetches all unread notifications for the staff member."""
    try:
        query = """
            SELECT notif_id, message, link, timestamp, is_read
            FROM notifications
            WHERE user_id = ? AND is_read = 0
            ORDER BY timestamp DESC
            LIMIT 10
        """
        # Changed %s to ? for SQLite compatibility
        cursor.execute(query, (staff_id,))
        return cursor.fetchall()
    except Exception as e:
        print(f"Error in fetch_unread_notifications: {e}", file=sys.stderr)
        return []