import pymysql
pymysql.install_as_MySQLdb()
import os
import sqlite3
import json
from flask import Flask, flash, render_template, request, redirect, session, url_for, abort, jsonify
from flask_socketio import SocketIO, emit, join_room
from dotenv import load_dotenv
from datetime import datetime
from flask_mail import Mail, Message
from flask_mysqldb import MySQL
import MySQLdb.cursors


# SECURITY IMPORTS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# DATABASE UTILS (Ensure these are updated to use '?' in db_utils.py)
from db_utils import fetch_unresolved_alerts, fetch_unread_notifications

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_secret_key_for_dev_only')

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'joydilys5@gmail.com'
app.config['MAIL_PASSWORD'] = 'nmydcqhfclhqkjyz'
app.config['MAIL_DEFAULT_SENDER'] = 'joydilys5@gmail.com'

mail = Mail(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Joydilys5?'
app.config['MYSQL_DB'] = 'fali_health_db'

mysql = MySQL(app)

# --- SQLite Configuration ---
DATABASE_FILE = 'home_health_db.db'

def get_db_connection():
    """Helper function to connect to the SQLite database."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row 
    return conn

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'staff_login'

class User(UserMixin):
    def __init__(self, user_id, username, password_hash, role='Staff'):
        # This 'self.id' is what Flask-Login uses internally
        self.id = str(user_id) 
        self.username = username
        self.password_hash = password_hash
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    db = get_db_connection()
    # Change 'user_id' to 'id' to match your init_db.py script
    user_data = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    db.close()
    if user_data:
        # Match the User object initialization to the column 'id'
        return User(user_data['id'], user_data['username'], user_data['password_hash'], user_data['role'])
    return None
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('join')
def on_join(data):
    room = data['room'] # Use appointment_id as the room name
    join_room(room)
    emit('status', {'msg': 'User joined the room.'}, room=room)

@socketio.on('signal')
def handle_signal(data):
    # Relays WebRTC signaling data (OFFER/ANSWER/ICE) to the other person in the room
    emit('signal', data, room=data['room'], include_self=False)
# --- AUTH ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact', methods=['POST'])
def contact_submit():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message_body = request.form.get('message')

        # Create the email message
        msg = Message(subject=f"New Contact Form Lead from {name}",
                      recipients=['your-destination-email@gmail.com']) # Where you want to receive it
        
        msg.body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message_body}"

        try:
            mail.send(msg)
            flash("Your message has been sent successfully!", "success")
        except Exception as e:
            flash(f"Error sending message: {str(e)}", "danger")

            confirm_msg = Message("We've received your inquiry - Fali Health",
                      recipients=[email])
            confirm_msg.body = f"Hello {name},\n\nThank you for reaching out to Fali Health. Our clinical team will review your message and get back to you shortly."
            mail.send(confirm_msg)

        return redirect(url_for('index'))
    


@app.route('/add_vitals', methods=['POST'])
def add_vitals():
    if 'patient_id' not in session:
        return redirect(url_for('patient_login'))
        
    p_id = session['patient_id']
    hr = request.form.get('heart_rate', type=int)
    sys = request.form.get('bp_sys', type=int)
    dia = request.form.get('bp_dia', type=int)
    glu = request.form.get('glucose', type=float)

    db = get_db_connection()
    db.row_factory = sqlite3.Row

    # 1. FETCH ADMIN THRESHOLDS
    # This ensures we use the exact limits set in your Admin screenshot
    limits = db.execute("""
        SELECT heart_rate_min, heart_rate_max, bp_systolic_max, bp_diastolic_max, glucose_max 
        FROM patients WHERE patient_id = ?
    """, (p_id,)).fetchone()

    # 2. AUTOMATIC ALERT LOGIC
    # We check the new data against the Admin's settings
    if limits:
        alert_msg = []
        if hr > limits['heart_rate_max'] or hr < limits['heart_rate_min']:
            alert_msg.append(f"Heart Rate ({hr}) out of range")
        if sys > limits['bp_systolic_max']:
            alert_msg.append(f"High Systolic BP ({sys})")
        if glu > limits['glucose_max']:
            alert_msg.append(f"High Glucose ({glu})")

        # If any limits were hit, insert into your 'alerts' table
        for msg in alert_msg:
            db.execute("""
                INSERT INTO alerts (patient_id, alert_type, message) 
                VALUES (?, 'Vitals Warning', ?)
            """, (p_id, msg))

    # 3. SAVE THE DATA
    db.execute("""
        INSERT INTO healthdata (patient_id, heart_rate, bp_systolic, bp_diastolic, glucose)
        VALUES (?, ?, ?, ?, ?)
    """, (p_id, hr, sys, dia, glu))

    db.commit()
    db.close()

    return redirect(url_for('patient_dashboard', patient_id=p_id))

@app.route('/services/<service_slug>')
def service_detail(service_slug):
    services_data = {
        'home-nursing': {
            'title': 'Home Nursing Care Services',
            'description': 'Professional clinical care and medical monitoring provided by registered nurses in the comfort of your home.',
            'features': ['Wound Management', 'Medication Administration', 'Post-Surgical Care', 'Vital Sign Monitoring']
        },
        'therapy': {
            'title': 'Therapy Services',
            'description': 'Comprehensive physical and occupational therapy designed to restore mobility and improve quality of life.',
            'features': ['Physiotherapy', 'Occupational Therapy', 'Speech Therapy', 'Rehabilitation Exercises']
        },
        'diet-planning': {
            'title': 'Diet Planning & Nutrition',
            'description': 'Expert nutritional consultation and personalized meal planning tailored to your specific clinical needs.',
            'features': ['Clinical Nutrition', 'Meal Planning', 'Weight Management', 'Diabetes Diet Support']
        },
        'counselling': {
            'title': 'Counselling Services',
            'description': 'Professional mental health support for patients and families navigating the challenges of chronic illness.',
            'features': ['Individual Therapy', 'Family Support', 'Grief Counselling', 'Stress Management']
        },
        'equipment-training': {
            'title': 'Equipment & Training',
            'description': 'Provision of high-grade medical equipment and specialized training for home caregivers.',
            'features': ['RPM Device Setup', 'Caregiver Workshops', 'Safety Training', 'Equipment Maintenance']
        }
    }

    service = services_data.get(service_slug)
    if not service:
        abort(404)
        
    return render_template('service_detail.html', service=service)



@app.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db_connection()
        user_row = db.execute('SELECT id, username, password_hash, role FROM users WHERE username = ?', (username,)).fetchone()
        db.close()

        if user_row and check_password_hash(user_row['password_hash'], password):
            user_obj = User(user_row['id'], user_row['username'], user_row['password_hash'], user_row['role'])
            login_user(user_obj)
            
            # --- ADD THIS LINE TO FIX THE REDIRECT ---
            session['role'] = user_row['role'] 
            # -----------------------------------------
            
            return redirect(url_for('staff_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            
    return render_template('staff_login.html')

# Route to render the consultation room
@app.route('/start_consultation/<int:appt_id>')
def start_consultation(appt_id):
    db = get_db_connection()
    # Updated query: Changed 'JOIN staff s' to 'JOIN users s' 
    # and 's.staff_id' to 's.id'
    appt = db.execute('''
        SELECT a.*, p.name as patient_name, s.username as doctor_name 
        FROM appointments a 
        JOIN patients p ON a.patient_id = p.patient_id 
        JOIN users s ON a.doctor_user_id = s.id 
        WHERE a.appt_id = ?
    ''', (appt_id,)).fetchone()
    db.close()
    
    if appt is None:
        return "Appointment not found", 404
        
    return render_template('consultation.html', appt=appt)

# Signaling via SocketIO
@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)

@socketio.on('signal')
def handle_signal(data):
    emit('signal', data, room=data['room'], include_self=False)

@app.route('/api/vitals/push', methods=['POST'])
def push_vitals():
    # 1. Get the JSON data from the device/app
    data = request.get_json()
    
    # Validation: Ensure we have the required fields
    required = ['patient_id', 'heart_rate', 'bp_sys', 'bp_dia', 'glucose']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing data fields"}), 400

    try:
        db = get_db_connection()
        db.execute("""
            INSERT INTO healthdata (patient_id, heart_rate, bp_systolic, bp_diastolic, glucose)
            VALUES (?, ?, ?, ?, ?)
        """, (data['patient_id'], data['heart_rate'], data['bp_sys'], data['bp_dia'], data['glucose']))
        db.commit()
        db.close()
        
        return jsonify({"status": "success", "message": "Vitals recorded"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        
        db = get_db_connection()
        patient = db.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
        db.close()

        if patient:
            # Store the patient ID in the session to "log them in"
            session['patient_id'] = patient['patient_id']
            flash(f"Welcome back, {patient['name']}!", "success")
            return redirect(url_for('patient_dashboard', patient_id=patient['patient_id']))
        else:
            flash("Invalid Patient ID.", "danger")
            
    return render_template('patient_login.html')# --- PATIENT DATA LOGIC (Converted to SQLite) ---

def get_patient_health_data(patient_id):
    db = get_db_connection()
    # This line is the secret sauce: it makes rows behave like dictionaries
    db.row_factory = sqlite3.Row 
    
    # 1. Fetch health data
    raw_health = db.execute("""
        SELECT timestamp, 
               heart_rate, 
               bp_systolic AS bp_sys, 
               bp_diastolic AS bp_dia, 
               glucose
        FROM healthdata
        WHERE patient_id = ?
        ORDER BY timestamp DESC LIMIT 20
    """, (patient_id,)).fetchall()

    # Convert list of Rows to list of dicts
    health_data = [dict(row) for row in raw_health]

    # 2. Fetch thresholds
    row_thresholds = db.execute("""
        SELECT heart_rate_min, 
               heart_rate_max, 
               bp_systolic_max, 
               bp_diastolic_max, 
               glucose_max 
        FROM patients 
        WHERE patient_id = ?
    """, (patient_id,)).fetchone()
    
    db.close()
    
    # Return both as clean dictionaries
    thresholds = dict(row_thresholds) if row_thresholds else {}
    return health_data, thresholds
# --- DASHBOARD ROUTES ---

@app.route('/dashboard')
@login_required
def staff_dashboard():
    """Main Monitoring Dashboard."""
    db = get_db_connection()
    
    # 1. Fetch unread notifications
    notifications = db.execute("""
        SELECT notif_id, message, link, timestamp, is_read
        FROM notifications WHERE user_id = ? AND is_read = 0
        ORDER BY timestamp DESC LIMIT 10
    """, (current_user.id,)).fetchall()

    # 2. Fetch unresolved alerts
    alerts = db.execute("""
        SELECT a.alert_id, a.timestamp, a.alert_type, p.name, p.patient_id, a.message
        FROM alerts a
        JOIN patients p ON a.patient_id = p.patient_id
        WHERE a.is_resolved = 0
        ORDER BY a.timestamp DESC LIMIT 5
    """).fetchall()

    # 3. Fetch ALL patient data (Changed to SELECT *)
    # This ensures name, clinical_status, and contact_info are available
    patients = db.execute("SELECT * FROM patients ORDER BY patient_id DESC").fetchall()

    # 4. Count pending appointments
    # Note: Using fetchone()[0] to get the integer count directly
    pending_count = db.execute("""
        SELECT COUNT(*) FROM appointments 
        WHERE status LIKE 'Pending%'
    """).fetchone()[0]

    # 5. NEW: Count patients specifically in the Lab Queue
    # This fixes the UndefinedError in dashboard_frame.html
    patients_count = db.execute("""
        SELECT COUNT(*) FROM patients 
        WHERE clinical_status = 'In Lab' AND is_active = 1
    """).fetchone()[0]

    db.close()
    
    # Make sure 'dashboard_frame.html' is actually the file displaying your patient list
    return render_template('dashboard_frame.html', 
                           alerts=alerts, 
                           patients=patients, 
                           notifications=notifications,
                           pending_count=pending_count,
                           patients_count=patients_count) # Pass the count here
@app.route('/test-vitals')
def test_vitals():
    db = get_db_connection()
    # Adding a fake reading for Patient #1
    db.execute("""
        INSERT INTO healthdata (patient_id, heart_rate, bp_systolic, bp_diastolic, glucose)
        VALUES (1, 75, 120, 80, 95.5)
    """)
    db.commit()
    db.close()
    return "Test vitals added! Go check the Reports page."
@app.route('/staff/update_appointment_status', methods=['POST'])
@login_required
def update_appointment_status():
    appt_id = request.form.get('appt_id')
    new_status = request.form.get('new_status')
    
    db = get_db_connection()
    
    # We update the status while keeping the original notes if they exist
    # Or simply overwrite it with the new status (e.g., "Confirmed")
    db.execute("UPDATE appointments SET status = ? WHERE appt_id = ?", (new_status, appt_id))
    db.commit()
    db.close()
    
    return redirect(url_for('manage_appointments')) 

@app.route('/staff/manage-appointments') # This is the URL
@login_required
def manage_appointments(): # THIS name must match the url_for()
    db = get_db_connection()
    # Fetching appointments with patient name and doctor name
    appointments = db.execute("""
        SELECT a.appt_id, a.appt_time, a.status, p.name as patient_name, p.patient_id, u.username as doctor_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN users u ON a.doctor_user_id = u.id
        ORDER BY a.appt_time DESC
    """).fetchall()
    db.close()
    return render_template('manage_appointments.html', appointments=appointments)                              

@app.route('/staff/reports')
@login_required
def clinical_reports():
    db = get_db_connection()
    try:
        # We start from 'patients' so everyone shows up even without readings
        reports = db.execute("""
            SELECT 
                p.name, 
                h.heart_rate, 
                h.bp_systolic, 
                h.bp_diastolic, 
                h.timestamp,
                p.clinical_status as status_summary
            FROM patients p
            LEFT JOIN healthdata h ON p.patient_id = h.patient_id
            ORDER BY h.timestamp DESC LIMIT 20
        """).fetchall()
    except Exception as e:
        print(f"Error fetching reports: {e}")
        reports = []
    finally:
        db.close()
    return render_template('reports.html', reports=reports)
@app.route('/staff/billing')
@login_required
def billing_receipts():
    db = get_db_connection()
    # Updated query: Focuses on the BILLING table first, then joins patient info
    billables = db.execute("""
        SELECT 
            b.bill_id as appt_id, 
            p.name as patient_name, 
            b.created_at as appt_time, 
            p.clinical_status as department, 
            'Medical Staff' as doctor_name, 
            b.amount as base_fee
        FROM billing b
        JOIN patients p ON b.patient_id = p.patient_id
        ORDER BY b.created_at DESC
    """).fetchall()
    db.close()
    return render_template('billing.html', billables=billables)

@app.route('/patient/register', methods=['GET', 'POST'])
@login_required
def patient_register():
    if request.method == 'POST':
        db = get_db_connection()
        try:
            # We map the HTML 'name' attributes to the DB column names
            db.execute("""
                INSERT INTO patients (
                    name, 
                    contact_info, 
                    heart_rate_min, 
                    heart_rate_max, 
                    bp_systolic_max,  -- Matches your init_db.py
                    bp_diastolic_max, -- Matches your init_db.py
                    glucose_max,
                    clinical_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Monitoring')
            """, (
                request.form.get('name'), 
                request.form.get('contact_info'),
                request.form.get('heart_rate_min', 60),
                request.form.get('heart_rate_max', 100),
                request.form.get('bp_sys_max', 140), # Maps HTML 'bp_sys_max' to DB 'bp_systolic_max'
                request.form.get('bp_dia_max', 90),  # Maps HTML 'bp_dia_max' to DB 'bp_diastolic_max'
                request.form.get('glucose_max', 180.0)
            ))
            db.commit()
            flash("Patient registered successfully!", "success")
            
            # Redirect to manage_patients with the success flag for the toast notification
            return redirect(url_for('manage_patients', registered='true'))
            
        except Exception as e:
            print(f"Registration Error: {e}")
            flash(f"Error: {e}", "danger")
        finally:
            db.close()
            
    return render_template('patient_register.html')


@app.route('/staff/patients/manage')
@login_required
def manage_patients():
    db = get_db_connection()
    try:
        patients = db.execute("""
            SELECT patient_id, name, contact_info, heart_rate_min, heart_rate_max,
                   bp_systolic_max, bp_diastolic_max, glucose_max, lifeline_status
            FROM patients ORDER BY patient_id DESC
        """).fetchall()
        db.close()
        return render_template('manage_patients.html', patients=patients)
    except Exception as e:
        app.logger.error(f"Error fetching patient list: {e}")
        return redirect(url_for('staff_dashboard'))

@app.route('/doctor_analysis/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def doctor_analysis_page(patient_id):
    db = get_db_connection()
    if request.method == 'POST':
        symptoms = request.form.get('symptoms')
        interpretation = request.form.get('test_interpretation')
        diagnosis = request.form.get('last_diagnosis_summary')

        db.execute("""
            UPDATE patients SET 
            symptoms = ?, test_interpretation = ?, last_diagnosis_summary = ?
            WHERE patient_id = ?
        """, (symptoms, interpretation, diagnosis, patient_id))
        db.commit()
        db.close()
        # REDIRECT to the same page but tell it to open the decision tab
        return redirect(url_for('doctor_analysis_page', patient_id=patient_id, tab='decision'))

    patient = db.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
    db.close()
    # Check if we should auto-open a specific tab
    active_tab = request.args.get('tab', 'analysis')
    return render_template('patient_workspace.html', patient=patient, active_tab=active_tab)        

@app.route('/health_trends/<int:patient_id>')
@login_required
def health_trends(patient_id):
    db = get_db_connection()
    patient = db.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
    db.close()

    if not patient:
        flash("Patient not found.", 'danger')
        return redirect(url_for('staff_dashboard'))

    return render_template('health_trends.html', patient=patient, patient_id=patient_id)

@app.route('/staff/patient_workspace/<int:patient_id>')
@login_required
def patient_workspace(patient_id):
    db = get_db_connection()
    patient = db.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
    db.close()
    if not patient:
        flash("Patient not found", "danger")
        return redirect(url_for('manage_patients'))
    
    # This single template will now handle the different "views" via tabs
    return render_template('patient_workspace.html', patient=patient)

    # 1. Send to Lab
@app.route('/staff/send_to_lab/<int:patient_id>')
@login_required
def send_to_lab(patient_id):
    db = get_db_connection()
    db.execute("UPDATE patients SET clinical_status = 'In Lab' WHERE patient_id = ?", (patient_id,))
    db.commit()
    db.close()
    flash("Patient sent to Lab department.", "info")
    return redirect(url_for('manage_patients'))

# 2. Lab Results Page (Dynamic Form)
@app.route('/staff/lab_entry/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def lab_entry(patient_id):
    db = get_db_connection()
    if request.method == 'POST':
        results = request.form.get('lab_results')
        db.execute("UPDATE patients SET lab_results = ?, clinical_status = 'Results Ready' WHERE patient_id = ?", 
                   (results, patient_id))
        db.commit()
        db.close()
        return redirect(url_for('manage_patients'))
    
    patient = db.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
    return render_template('lab_entry.html', patient=patient)

# 3. Final Disposition (Admit / Pharmacy)

@app.route('/staff/disposition/<int:patient_id>', methods=['POST'])
@login_required
def set_disposition(patient_id):
    choice = request.form.get('disposition') 
    p_notes = request.form.get('pharmacy_notes') # Get the doctor's prescription text
    
    db = get_db_connection()
    if choice == 'Admit':
        status = 'Admitted to Ward'
    else:
        status = 'Sent to Pharmacy'
    
    db.execute("UPDATE patients SET clinical_status = ?, pharmacy_notes = ? WHERE patient_id = ?", 
               (status, p_notes, patient_id))
    db.commit()
    db.close()
    return redirect(url_for('manage_patients'))

@app.route('/staff/lab_dashboard')
def lab_dashboard():
    # Check if user is logged in
    # if 'user_id' not in session:
    #     return redirect(url_for('staff_login'))

    user_role = session.get('role')
    
    # Allowed roles for the lab
    allowed = ['Staff', 'Admin', 'Doctor', 'Lab', 'Medical Staff']

    # If the role is missing or not allowed, go to Management, NOT Login
    if user_role not in allowed:
        flash(f"Access Denied: Your role ({user_role}) cannot view the Lab Queue.")
        return redirect(url_for('manage_patients'))

    db = get_db_connection()
    try:
        # UPDATED QUERY: Uses 'patient_id' and 'name' directly from the patients table
        patients = db.execute("""
            SELECT 
                patient_id, 
                name, 
                test_interpretation,
                clinical_status
            FROM patients 
            WHERE clinical_status = 'In Lab'
        """).fetchall()
        db.close()
        
        return render_template('lab_dashboard.html', patients=patients)
        
    except sqlite3.OperationalError as e:
        if db: db.close()
        return f"Database Error: {str(e)}. Check your SQL syntax or column names."



@app.route('/staff/pharmacy_dashboard')
@login_required
def pharmacy_dashboard():
    db = get_db_connection()
    # Only show patients whose status is 'Sent to Pharmacy'
    patients = db.execute("SELECT * FROM patients WHERE clinical_status = 'Sent to Pharmacy' AND is_active = 1").fetchall()
    db.close()
    return render_template('pharmacy_dashboard.html', patients=patients)

@app.route('/staff/pharmacy/release/<int:patient_id>', methods=['POST'])
@login_required
def release_patient(patient_id):
    db = get_db_connection()
    db.execute("UPDATE patients SET clinical_status = 'Discharged' WHERE patient_id = ?", (patient_id,))
    db.commit()
    db.close()
    
    # This flashes a link that the pharmacist can click to see the summary
    flash(f"Patient released! <a href='/staff/discharge_summary/{patient_id}' target='_blank' class='font-bold underline'>Click here to print Discharge Summary</a>", "success")
    return redirect(url_for('pharmacy_dashboard'))

@app.route('/patient/<int:patient_id>/schedule_consultations')
@login_required
def schedule_consultations(patient_id):
    db = get_db_connection()
    
    # 1. Fetch appointments to show in the list
    appointments = db.execute("SELECT * FROM appointments WHERE patient_id = ?", (patient_id,)).fetchall()
    
    # 2. Fetch doctors for the dropdown
    doctors = db.execute("SELECT user_id, username FROM users WHERE role = 'Staff'").fetchall()
    
    db.close()
    
    # 3. Pass EVERYTHING to the template
    return render_template('schedule_consultations.html', 
                           appointments=appointments, 
                           patient_id=patient_id, 
                           doctors=doctors)
@app.route('/staff/dashboard/content')
@login_required
def main_dashboard_content():
    """Provides the inner content for the staff dashboard iframe."""
    db = get_db_connection()
    
    # 1. Fetch patients for the summary table
    patients = db.execute("SELECT * FROM patients ORDER BY patient_id DESC LIMIT 10").fetchall()
    
    # 2. Fetch recent alerts
    alerts = db.execute("""
        SELECT a.*, p.name 
        FROM alerts a 
        JOIN patients p ON a.patient_id = p.patient_id 
        WHERE a.is_resolved = 0 
        ORDER BY a.timestamp DESC LIMIT 5
    """).fetchall()
    
    db.close()
    return render_template('main_dashboard_content.html', patients=patients, alerts=alerts)
    
@app.route('/api/vitals/<int:patient_id>', methods=['GET'])
@login_required
def get_patient_vitals_api(patient_id):
    try:
        db = get_db_connection()
        vitals_data = db.execute("""
            SELECT timestamp, heart_rate, bp_systolic, bp_diastolic, glucose_level
            FROM healthdata WHERE patient_id = ?
            ORDER BY timestamp ASC LIMIT 50
        """, (patient_id,)).fetchall()
        db.close()

        data = {
            'labels': [entry['timestamp'] for entry in vitals_data],
            'heart_rate': [entry['heart_rate'] for entry in vitals_data],
            'bp_systolic': [entry['bp_systolic'] for entry in vitals_data],
            'bp_diastolic': [entry['bp_diastolic'] for entry in vitals_data],
            'glucose_level': [entry['glucose_level'] for entry in vitals_data]
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/staff/patients/edit/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def patient_edit(patient_id):
    db = get_db_connection()
    if request.method == 'POST':
        try:
            db.execute("""
                UPDATE patients SET
                    name = ?, contact_info = ?, heart_rate_min = ?,
                    heart_rate_max = ?, bp_sys_max = ?, bp_dia_max = ?,
                    glucose_max = ?
                WHERE patient_id = ?
            """, (request.form['name'], request.form['contact_info'], 
                  request.form['hr_min'], request.form['hr_max'],
                  request.form['bp_sys_max'], request.form['bp_dia_max'],
                  request.form['glucose_max'], patient_id))
            db.commit()
            flash("Patient updated successfully.", 'success')
            return redirect(url_for('manage_patients'))
        except Exception as e:
            flash(f"Error: {e}", 'danger')
        finally:
            db.close()

    patient = db.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
    db.close()
    return render_template('patient_edit.html', patient=patient)

@app.route('/staff/patients/delete/<int:patient_id>', methods=['POST', 'GET'])
@login_required
def patient_delete(patient_id):
    db = get_db_connection()
    try:
        # SQLite uses ? instead of %s
        db.execute("DELETE FROM alerts WHERE patient_id = ?", (patient_id,))
        db.execute("DELETE FROM healthdata WHERE patient_id = ?", (patient_id,))
        db.execute("DELETE FROM patients WHERE patient_id = ?", (patient_id,))
        db.commit()
        flash(f"Patient ID {patient_id} deleted.", 'success')
    except Exception as e:
        db.rollback()
        flash(f"Error: {e}", 'danger')
    finally:
        db.close()
    return redirect(url_for('manage_patients'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been successfully logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/finalize_decision/<int:patient_id>', methods=['POST'])
@login_required
def surgery_decision_page(patient_id):
    db = get_db_connection()
    decision = request.form.get('decision_type')
    notes = request.form.get('pharmacy_notes')
    billable_item = request.form.get('billable_item') # e.g. "Metformin - $20.00"

    # Extract the price (everything after the $)
    try:
        price = float(billable_item.split('$')[1])
    except:
        price = 0.0

    # 1. Update Patient Path
    db.execute("UPDATE patients SET clinical_status = ?, pharmacy_notes = ? WHERE patient_id = ?", 
               (decision, notes, patient_id))

    # 2. Add to Billing Table
    db.execute("INSERT INTO billing (patient_id, amount, payment_status) VALUES (?, ?, 'Unpaid')", 
               (patient_id, price))
    
    db.commit()
    db.close()
    return redirect(url_for('manage_patients'))

@app.route('/patient_entry', methods=['GET', 'POST'])
def patient_data_entry():
    db = get_db_connection()
    if request.method == 'POST':
        try:
            patient_id = request.form['patient_id']
            hr = int(request.form['heart_rate'])
            bp_sys, bp_dia = map(int, request.form['blood_pressure'].split('/'))
            glucose = float(request.form['glucose_level'])

            db.execute("""
                INSERT INTO healthdata (patient_id, heart_rate, bp_systolic, bp_diastolic, glucose_level, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (patient_id, hr, bp_sys, bp_dia, glucose, datetime.now()))
            
            db.commit()
            flash(f"Data received for Patient {patient_id}.", 'success')
            return redirect(url_for('patient_data_entry'))
        except Exception as e:
            flash(f"Error: {e}", 'danger')
        finally:
            db.close()

    patients = db.execute("SELECT patient_id, name FROM patients").fetchall()
    db.close()
    return render_template('patient_data_entry.html', patients=patients)

    # Handle GET request (render the form)
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT patient_id, name FROM patients")
        patients = cur.fetchall()
        cur.close()
    except Exception as e:
        app.logger.error(f"Error fetching patient list for data entry form: {e}")
        patients = [] 

    return render_template('patient_data_entry.html', patients=patients)


@app.route('/api/alert/<int:alert_id>/resolve', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    """API endpoint to resolve an alert."""
    try:
        cur = mysql.connection.cursor()
        # Update lowercase 'alerts'
        cur.execute("UPDATE alerts SET is_resolved = 1 WHERE alert_id = %s", [alert_id])
        mysql.connection.commit()
        cur.close()
        return jsonify({'message': 'Alert resolved successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/patient/<int:patient_id>/dashboard')
def patient_dashboard(patient_id):
    print(f"DEBUG: Accessing dashboard for ID {patient_id}")
    if 'patient_id' not in session or session['patient_id'] != patient_id:
        return redirect(url_for('patient_login'))

    db = get_db_connection()

    # 1. Fetch raw data using your helper
    raw_readings, raw_thresholds = get_patient_health_data(patient_id)

    # 2. Fetch list of Doctors for the dropdown
    doctors = db.execute("SELECT id, username FROM users WHERE role IN ('Doctor', 'Staff')").fetchall()

    # 3. Fetch patient's appointments - UPDATED TO INCLUDE appt_id
    appointments = db.execute("""
        SELECT a.appt_id, a.appt_time, a.status, u.username as doctor_name
        FROM appointments a
        LEFT JOIN users u ON a.doctor_user_id = u.id
        WHERE a.patient_id = ?
        ORDER BY a.appt_time DESC
    """, (patient_id,)).fetchall()

    db.close()

    # 4. Reformat for Chart.js
    health_data = {
        "labels": [str(r['timestamp']) for r in raw_readings][::-1],
        "heart_rate": [r['heart_rate'] for r in raw_readings][::-1],
        "systolic": [r['bp_sys'] for r in raw_readings][::-1],
        "diastolic": [r['bp_dia'] for r in raw_readings][::-1],
        "glucose": [float(r['glucose']) if r['glucose'] else 0 for r in raw_readings][::-1]
    }

    # 5. Format thresholds
    thresholds = {
        "hr_limit": raw_thresholds.get('heart_rate_max', 100) if raw_thresholds else 100,
        "sys_limit": raw_thresholds.get('bp_systolic_max', 140) if raw_thresholds else 140,
        "dia_limit": raw_thresholds.get('bp_diastolic_max', 90) if raw_thresholds else 90,
        "glucose_limit": raw_thresholds.get('glucose_max', 180) if raw_thresholds else 180
    }

    return render_template('patient_dashboard.html', 
                           patient_id=patient_id,
                           health_data=health_data, 
                           thresholds=thresholds,
                           doctors=doctors,
                           appointments=appointments)

@app.route('/patient/<int:patient_id>/appointments')
def patient_appointments(patient_id):
    if 'patient_id' not in session or session['patient_id'] != patient_id:
        return redirect(url_for('patient_login'))
    
    cur = mysql.connection.cursor()
    
    # 1. Fetch existing appointments for this patient
    cur.execute("""
        SELECT a.appt_time, a.status, u.username as doctor_name
        FROM appointments a
        JOIN users u ON a.doctor_user_id = u.user_id
        WHERE a.patient_id = %s
        ORDER BY a.appt_time DESC
    """, [patient_id])
    appointments_list = cur.fetchall()
    
    # 2. Fetch doctors for the "Book" dropdown
    cur.execute("SELECT user_id, username FROM users WHERE role IN ('Staff', 'Admin')")
    doctors = cur.fetchall()
    
    cur.close()
    return render_template('appointments.html', 
                           patient_id=patient_id, 
                           appointments=appointments_list, 
                           doctors=doctors)

# The name here MUST be 'book_appointment'
@app.route('/patient/book_appointment', methods=['POST'])
def book_appointment():
    # Make sure we know which patient is booking
    patient_id = session.get('patient_id')
    if not patient_id:
        return redirect(url_for('patient_login'))

    doctor_id = request.form.get('doctor_id')
    dept = request.form.get('department')
    reason = request.form.get('reason')
    appt_time = f"{request.form.get('appointment_date')} {request.form.get('appointment_time')}"
    
    # Pack extra info into status to avoid DB schema changes
    combined_status = f"Pending | Dept: {dept} | Note: {reason}"

    db = get_db_connection()
    db.execute("""
        INSERT INTO appointments (patient_id, doctor_user_id, appt_time, status)
        VALUES (?, ?, ?, ?)
    """, (patient_id, doctor_id, appt_time, combined_status))
    db.commit()
    db.close()

    # Fixed the BuildError by passing patient_id
    return redirect(url_for('patient_dashboard', patient_id=patient_id))

@app.route('/register_staff', methods=['GET', 'POST'])
@login_required
def register_staff():
    # Only allow existing Admins/Staff to create new doctors
    if current_user.role != 'Admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('staff_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'Staff')

        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

        cur = mysql.connection.cursor()
        try:
            cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)", 
                        (username, hashed_pw, role))
            mysql.connection.commit()
            flash(f'Doctor {username} registered successfully!', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            cur.close()
            
    return render_template('register_staff.html')

@app.route('/accept_appointment/<int:appt_id>')
@login_required
def accept_appointment(appt_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE appointments SET status = 'Confirmed' WHERE appt_id = %s", [appt_id])
    mysql.connection.commit()
    cur.close()
    flash('Appointment Confirmed!', 'success')
    return redirect(url_for('staff_dashboard'))

@app.route('/diagnose/<int:patient_id>', methods=['GET', 'POST'], endpoint='diagnose_patient')
@login_required
def diagnose_patient(patient_id):
    # Use DictCursor so v['column_name'] works
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
    
    if request.method == 'POST':
        notes = request.form.get('notes')
        decision = request.form.get('decision')
        # Update your database logic here
        cur.execute("UPDATE patients SET analysis_notes=%s, decision_type=%s WHERE patient_id=%s", 
                    (notes, decision, patient_id))
        mysql.connection.commit()
        cur.close()
        flash('Diagnosis submitted successfully!', 'success')
        return redirect(url_for('staff_dashboard'))

    # GET: Fetch health data
    cur.execute("SELECT * FROM healthdata WHERE patient_id = %s ORDER BY timestamp DESC LIMIT 20", [patient_id])
    vitals = cur.fetchall()
    
    # Pre-process data for JS
    # Using v.get() handles missing columns; float() handles Decimal types from MySQL
    health_data = {
        "labels": [v['timestamp'].strftime('%H:%M') for v in vitals][::-1] if vitals else [],
        "heart_rate": [v.get('heart_rate', 0) for v in vitals][::-1],
        "glucose": [float(v.get('glucose', 0)) if v.get('glucose') else 0 for v in vitals][::-1]
    }
    
    thresholds = {"hr_limit": 100, "glucose_limit": 180}
    cur.close()
    
    return render_template('diagnose.html', 
                           patient_id=patient_id, 
                           vitals=vitals, 
                           health_data=health_data, 
                           thresholds=thresholds)





# if __name__ == '__main__':
#     # NOTE: Database setup is now handled via the 'flask init-db' command!
#     # Remove the 'create_tables()' call here.
#     app.run(debug=True)

if __name__ == '__main__':
    # Render provides a PORT environment variable, default to 5000 locally
    port = int(os.environ.get("PORT", 5000))
    # host="0.0.0.0" tells Flask to accept connections from outside
    app.run(host="0.0.0.0", port=port)