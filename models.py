# models.py
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime

# single SQLAlchemy instance (do NOT init here)
db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin','doctor','patient'

    def set_password(self, pw):
        self.password_hash = pw   # store directly

    def check_password(self, pw):
        return self.password_hash == pw


class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True)
    description = db.Column(db.Text)


class Doctor(db.Model):
    __tablename__ = 'doctors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fullname = db.Column(db.String(120), nullable=False)
    specialization = db.Column(db.String(120), nullable=False)
    availability = db.Column(db.Text)  # simple semicolon-separated slots


class Patient(db.Model):
    __tablename__ = 'patients'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fullname = db.Column(db.String(120), nullable=False)
    contact = db.Column(db.String(50))


class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(20), nullable=False)  # "09:00-09:30"
    status = db.Column(db.String(20), default='Booked')  # Booked / Completed / Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Treatment(db.Model):
    __tablename__ = 'treatments'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)


def create_db_and_admin(app):
    """
    Create tables programmatically and add a default admin (only if missing).
    Important: do NOT call db.init_app(app) here (init only once in app.py).
    """
    with app.app_context():
        db.create_all()
        # create default admin if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')   # change when you submit
            db.session.add(admin)
            db.session.commit()
            print("Admin created: username=admin password=admin123")
