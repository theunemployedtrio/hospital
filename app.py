from flask import Flask, render_template, url_for, request, session, redirect
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

@app.route("/" , methods = ["POST", "GET"])



         
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Doctor, Patient, Department, Appointment, Treatment, DoctorAvailability
from datetime import datetime, timedelta

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database with app
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to login if user not authenticated
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Initialize database and create admin
def init_db():
    """Create database tables and admin user if they don't exist"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin already exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                email='admin@hospital.com',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            
            # Create some default departments
            departments_data = [
                {'name': 'Cardiology', 'description': 'Heart and cardiovascular system care'},
                {'name': 'Neurology', 'description': 'Brain and nervous system disorders'},
                {'name': 'Orthopedics', 'description': 'Bone, joint, and muscle treatment'},
                {'name': 'Pediatrics', 'description': 'Healthcare for infants, children, and adolescents'},
                {'name': 'General Medicine', 'description': 'General health and wellness'},
                {'name': 'Dermatology', 'description': 'Skin, hair, and nail conditions'},
                {'name': 'Oncology', 'description': 'Cancer diagnosis and treatment'},
            ]
            
            for dept_data in departments_data:
                dept = Department(name=dept_data['name'], description=dept_data['description'])
                db.session.add(dept)
            
            # Commit changes
            db.session.commit()
            print("=" * 50)
            print("DATABASE INITIALIZED SUCCESSFULLY!")
            print("=" * 50)
            print("Admin Login Credentials:")
            print("Username: admin")
            print("Password: admin123")
            print("=" * 50)


# ============================================
# BASIC ROUTES
# ============================================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for all users"""
    # If user already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Find user in database
        user = User.query.filter_by(username=username).first()
        
        # Check if user exists and password is correct
        if user and check_password_hash(user.password, password):
            # Check if doctor/patient is active
            if user.role == 'doctor':
                if not user.doctor_profile or not user.doctor_profile.is_active:
                    flash('Your account has been deactivated. Contact admin.', 'danger')
                    return redirect(url_for('login'))
            elif user.role == 'patient':
                if not user.patient_profile or not user.patient_profile.is_active:
                    flash('Your account has been deactivated. Contact admin.', 'danger')
                    return redirect(url_for('login'))
            
            # Login successful
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Redirect to next page if exists, otherwise dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Patient registration page"""
    # If user already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        contact = request.form.get('contact')
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already taken. Please choose another.', 'danger')
            return redirect(url_for('register'))
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please use another.', 'danger')
            return redirect(url_for('register'))
        
        # Create new patient user
        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role='patient'
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Create patient profile
        new_patient = Patient(
            user_id=new_user.id,
            full_name=full_name,
            contact=contact
        )
        db.session.add(new_patient)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard - redirects based on user role"""
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    elif current_user.role == 'patient':
        return redirect(url_for('patient_dashboard'))
    else:
        flash('Invalid user role', 'danger')
        return redirect(url_for('logout'))


@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))


# ============================================
# ADMIN ROUTES (Will be implemented next)
# ============================================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    if current_user.role != 'admin':
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get statistics for dashboard
    total_doctors = Doctor.query.filter_by(is_active=True).count()
    total_patients = Patient.query.filter_by(is_active=True).count()
    total_appointments = Appointment.query.count()
    today = datetime.today().date()
    today_appointments = Appointment.query.filter_by(appointment_date=today).count()
    
    # Get recent appointments
    recent_appointments = Appointment.query.order_by(
        Appointment.created_at.desc()
    ).limit(10).all()
    
    # Get all departments
    departments = Department.query.all()
    
    return render_template('admin/dashboard.html',
                         total_doctors=total_doctors,
                         total_patients=total_patients,
                         total_appointments=total_appointments,
                         today_appointments=today_appointments,
                         recent_appointments=recent_appointments,
                         departments=departments)


# ============================================
# DOCTOR ROUTES (Will be implemented next)
# ============================================

@app.route('/doctor/dashboard')
@login_required
def doctor_dashboard():
    """Doctor dashboard"""
    if current_user.role != 'doctor':
        flash('Access denied. Doctor only.', 'danger')
        return redirect(url_for('dashboard'))
    
    doctor = current_user.doctor_profile
    
    # Get today's appointments
    today = datetime.today().date()
    today_appointments = Appointment.query.filter_by(
        doctor_id=doctor.id,
        appointment_date=today
    ).all()
    
    # Get upcoming appointments (next 7 days)
    next_week = today + timedelta(days=7)
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date >= today,
        Appointment.appointment_date <= next_week,
        Appointment.status == 'Booked'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    # Get all patients assigned to this doctor
    patients = Patient.query.join(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).distinct().all()
    
    return render_template('doctor/dashboard.html',
                         doctor=doctor,
                         today_appointments=today_appointments,
                         upcoming_appointments=upcoming_appointments,
                         patients=patients)


# ============================================
# PATIENT ROUTES (Will be implemented next)
# ============================================

@app.route('/patient/dashboard')
@login_required
def patient_dashboard():
    """Patient dashboard"""
    if current_user.role != 'patient':
        flash('Access denied. Patient only.', 'danger')
        return redirect(url_for('dashboard'))
    
    patient = current_user.patient_profile
    
    # Get all departments
    departments = Department.query.all()
    
    # Get upcoming appointments
    today = datetime.today().date()
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appointment_date >= today,
        Appointment.status == 'Booked'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    # Get past appointments with treatment
    past_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.status == 'Completed'
    ).order_by(Appointment.appointment_date.desc()).limit(10).all()
    
    return render_template('patient/dashboard.html',
                         patient=patient,
                         departments=departments,
                         upcoming_appointments=upcoming_appointments,
                         past_appointments=past_appointments)


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


# ============================================
# RUN APPLICATION
# ============================================

if __name__ == '__main__':
    init_db()
    app.run(debug=True)




















#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
#db = SQLAlchemy(app)

