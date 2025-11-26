# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Doctor, Patient, Appointment, Treatment, Department, create_db_and_admin
from datetime import datetime
#import os

#BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change_this_secret'  # change before final submission
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# initialize db once here
db.init_app(app)
# create tables and default admin
create_db_and_admin(app)


# ---------- Helpers ----------
def login_required(role=None):
    """
    Use like:
       guard = login_required('admin')()
       if guard: return guard
    This avoids decorator complexity for beginners.
    """
    def inner_guard():
        if 'user_id' not in session:
            flash('Please login first.')
            return redirect(url_for('login'))
        if role and session.get('role') != role:
            flash('Access denied.')
            return redirect(url_for('home'))
        return None
    return inner_guard


def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None


# ---------- Routes ----------
@app.route('/')
def home():
    # pass user so base.html can show username safely
    return render_template('home.html', user=get_current_user())


# Register (Patient)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        fullname = request.form['fullname'].strip()
        contact = request.form.get('contact', '').strip()
        if not username or not password or not fullname:
            flash('Please fill required fields.')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))
        u = User(username=username, role='patient')
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        p = Patient(user_id=u.id, fullname=fullname, contact=contact)
        db.session.add(p)
        db.session.commit()
        flash('Registration successful. Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')


# Login (all roles)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            flash('Logged in successfully.')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            flash('Invalid credentials.')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.')
    return redirect(url_for('home'))

# ---------------- Admin ----------------
@app.route('/admin')
def admin_dashboard():
    guard = login_required('admin')()
    if guard:
        return guard
    doctors = Doctor.query.all()
    patients = Patient.query.all()
    appointments = Appointment.query.order_by(Appointment.date.desc()).all()
    return render_template('admin_dashboard.html', doctors=doctors, patients=patients, appointments=appointments)


@app.route('/admin/create_doctor', methods=['GET', 'POST'])
def create_doctor():
    guard = login_required('admin')()
    if guard:
        return guard
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        fullname = request.form['fullname'].strip()
        specialization = request.form['specialization'].strip()
        if User.query.filter_by(username=username).first():
            flash('Username exists.')
            return redirect(url_for('create_doctor'))
        u = User(username=username, role='doctor')
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        d = Doctor(user_id=u.id, fullname=fullname, specialization=specialization, availability='')
        db.session.add(d)
        db.session.commit()
        flash('Doctor created.')
        return redirect(url_for('admin_dashboard'))
    return render_template('create_doctor.html')


@app.route('/admin/delete_doctor/<int:doctor_id>', methods=['POST'])
def delete_doctor(doctor_id):
    guard = login_required('admin')()
    if guard:
        return guard
    d = Doctor.query.get(doctor_id)
    if not d:
        flash('Doctor not found.')
        return redirect(url_for('admin_dashboard'))
    # optionally delete linked user or appointments (kept simple)
    db.session.delete(d)
    db.session.commit()
    flash('Doctor removed.')
    return redirect(url_for('admin_dashboard'))

# ---------------- Admin: Update Doctor ----------------
@app.route('/admin/update_doctor/<int:doctor_id>', methods=['GET', 'POST'])
def update_doctor(doctor_id):
    guard = login_required('admin')()
    if guard: return guard
    
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        flash("Doctor not found.")
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        doctor.fullname = request.form['fullname']
        doctor.specialization = request.form['specialization']
        db.session.commit()
        flash("Doctor updated successfully.")
        return redirect(url_for('admin_dashboard'))

    return render_template('update_doctor.html', doctor=doctor)

@app.route('/admin/search_patient')
def search_patient():
    guard = login_required('admin')()
    if guard: return guard

    q = request.args.get('q', '').strip()
    patients = []

    if q:
        patients = Patient.query.filter(
            (Patient.fullname.ilike(f"%{q}%")) |
            (Patient.contact.ilike(f"%{q}%"))
        ).all()

    return render_template('search_patient.html', patients=patients, q=q)

@app.route('/admin/delete_patient/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    guard = login_required('admin')()
    if guard: return guard

    p = Patient.query.get(patient_id)
    if not p:
        flash("Patient not found.")
        return redirect(url_for('admin_dashboard'))

    db.session.delete(p)
    db.session.commit()
    flash("Patient deleted.")
    return redirect(url_for('admin_dashboard'))


# ---------------- Patient ----------------
@app.route('/patient')
def patient_dashboard():
    guard = login_required('patient')()
    if guard:
        return guard
    user = get_current_user()
    patient = Patient.query.filter_by(user_id=user.id).first()
    departments = Department.query.all()
    doctors = Doctor.query.all()
    my_appts = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.date.desc()).all()
    return render_template('patient_dashboard.html', patient=patient, doctors=doctors, departments=departments, appts=my_appts)

@app.route('/patient/edit', methods=['GET', 'POST'])
def patient_edit():
    guard = login_required('patient')()
    if guard: return guard

    user = get_current_user()
    patient = Patient.query.filter_by(user_id=user.id).first()

    if request.method == 'POST':
        patient.fullname = request.form['fullname']
        patient.contact = request.form['contact']
        db.session.commit()
        flash("Profile updated.")
        return redirect(url_for('patient_dashboard'))

    return render_template('patient_edit.html', patient=patient)

@app.route('/search_doctors', methods=['GET'])
def search_doctors():
    q = request.args.get('q', '').strip()
    specialization = request.args.get('specialization', '').strip()
    if q:
        doctors = Doctor.query.filter(Doctor.fullname.ilike(f'%{q}%')).all()
    elif specialization:
        doctors = Doctor.query.filter(Doctor.specialization.ilike(f'%{specialization}%')).all()
    else:
        doctors = Doctor.query.all()
    return render_template('search_results.html', doctors=doctors)


@app.route('/book/<int:doctor_id>', methods=['GET', 'POST'])
def book(doctor_id):
    guard = login_required('patient')()
    if guard:
        return guard
    user = get_current_user()
    patient = Patient.query.filter_by(user_id=user.id).first()
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        flash('Doctor not found.')
        return redirect(url_for('patient_dashboard'))
    if request.method == 'POST':
        date_str = request.form['date'].strip()
        time_slot = request.form['time'].strip()
        if not date_str or not time_slot:
            flash('Please select date and time.')
            return redirect(url_for('book', doctor_id=doctor_id))
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.')
            return redirect(url_for('book', doctor_id=doctor_id))
        existing = Appointment.query.filter_by(doctor_id=doctor.id, date=dt, time=time_slot, status='Booked').first()
        if existing:
            flash('Slot already booked for this doctor. Choose another.')
            return redirect(url_for('book', doctor_id=doctor_id))
        existing_p = Appointment.query.filter_by(patient_id=patient.id, date=dt, time=time_slot, status='Booked').first()
        if existing_p:
            flash('You already have an appointment at this time.')
            return redirect(url_for('book', doctor_id=doctor_id))
        appt = Appointment(patient_id=patient.id, doctor_id=doctor.id, date=dt, time=time_slot, status='Booked')
        db.session.add(appt)
        db.session.commit()
        flash('Appointment booked successfully.')
        return redirect(url_for('patient_dashboard'))
    return render_template('book.html', doctor=doctor)


@app.route('/cancel_appointment/<int:appt_id>', methods=['POST'])
def cancel_appointment(appt_id):
    guard = login_required('patient')()
    if guard:
        return guard
    appt = Appointment.query.get(appt_id)
    if not appt:
        flash('Appointment not found.')
        return redirect(url_for('patient_dashboard'))
    user = get_current_user()
    patient = Patient.query.filter_by(user_id=user.id).first()
    if appt.patient_id != patient.id:
        flash('Access denied.')
        return redirect(url_for('patient_dashboard'))
    appt.status = 'Cancelled'
    db.session.commit()
    flash('Appointment cancelled.')
    return redirect(url_for('patient_dashboard'))


# ---------------- Doctor ----------------
@app.route('/doctor')
def doctor_dashboard():
    guard = login_required('doctor')()
    if guard:
        return guard
    user = get_current_user()
    doctor = Doctor.query.filter_by(user_id=user.id).first()
    appts = Appointment.query.filter_by(doctor_id=doctor.id).order_by(Appointment.date).all()
    return render_template('doctor_dashboard.html', doctor=doctor, appts=appts)


@app.route('/doctor/availability/<int:doctor_id>', methods=['GET', 'POST'])
def doctor_availability(doctor_id):
    guard = login_required('doctor')()
    if guard:
        return guard
    doc = Doctor.query.get(doctor_id)
    if request.method == 'POST':
        slots = request.form.get('availability', '').strip()
        doc.availability = slots
        db.session.commit()
        flash('Availability updated.')
        return redirect(url_for('doctor_dashboard'))
    return render_template('doctor_availability.html', doctor=doc)


@app.route('/doctor/mark_complete/<int:appt_id>', methods=['GET', 'POST'])
def mark_complete(appt_id):
    guard = login_required('doctor')()
    if guard:
        return guard
    appt = Appointment.query.get(appt_id)
    if not appt:
        flash('Appointment not found.')
        return redirect(url_for('doctor_dashboard'))
    user = get_current_user()
    doctor = Doctor.query.filter_by(user_id=user.id).first()
    if appt.doctor_id != doctor.id:
        flash('Access denied.')
        return redirect(url_for('doctor_dashboard'))
    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis', '').strip()
        prescription = request.form.get('prescription', '').strip()
        notes = request.form.get('notes', '').strip()
        appt.status = 'Completed'
        db.session.commit()
        t = Treatment(appointment_id=appt.id, diagnosis=diagnosis, prescription=prescription, notes=notes)
        db.session.add(t)
        db.session.commit()
        flash('Marked completed and treatment saved.')
        return redirect(url_for('doctor_dashboard'))
    return render_template('mark_complete.html', appt=appt)


# ---------------- View patient history ----------------
@app.route('/patient_history/<int:patient_id>')
def patient_history(patient_id):
    user = get_current_user()
    if 'user_id' not in session:
        flash('Login required.')
        return redirect(url_for('login'))
    allowed = False
    if session.get('role') == 'admin':
        allowed = True
    elif session.get('role') == 'doctor':
        allowed = True
    elif session.get('role') == 'patient':
        p = Patient.query.filter_by(user_id=user.id).first()
        if p and p.id == patient_id:
            allowed = True
    if not allowed:
        flash('Access denied.')
        return redirect(url_for('home'))
    patient = Patient.query.get(patient_id)
    appts = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.date.desc()).all()
    # make treatments accessible in template by relationship (SQLAlchemy lazy load)
    return render_template('patient_history.html', patient=patient, appts=appts)


# Run
if __name__ == '__main__':
    # debug True is fine during development. If you had issues with reloader earlier,
    # use use_reloader=False or set debug=False. For now keep debug=True for helpful errors.
    app.run(debug=True)
