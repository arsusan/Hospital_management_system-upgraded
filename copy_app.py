# Standard Library Imports
from datetime import datetime
import secrets
import json

# Flask Core Imports
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify

# Flask Extensions
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
from flask_login import (
    LoginManager, UserMixin, login_user, current_user,
    logout_user, login_required
)
from flask_wtf import FlaskForm
from flask_mail import Mail, Message

# WTForms Fields & Validators
from wtforms import (
    StringField, PasswordField, SubmitField,
    DateField, TimeField, BooleanField, SelectField
)
from wtforms.validators import DataRequired, Length, Email, EqualTo

# Initialize Flask-Migrate

# App Initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['MAIL_SERVER'] = 'smtp.example.com'  # Replace with your SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@example.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'your-email-password'  # Replace with your email password

# Initialize Extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)

# User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_doctor = db.Column(db.Boolean, default=False)
    specialization = db.Column(db.String(100))  # New field for doctor specialization

    # Relationships
    appointments_as_patient = db.relationship(
        'Appointment', foreign_keys='Appointment.patient_id',
        backref='patient', lazy=True
    )
    appointments_as_doctor = db.relationship(
        'Appointment', foreign_keys='Appointment.doctor_id',
        backref='doctor', lazy=True
    )
    availability = db.relationship('Availability', backref='doctor', lazy=True)

class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    is_booked = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'start_time', 'end_time', name='unique_availability_slot'),
    )

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='Pending')

# Initialize Database
with app.app_context():
    db.create_all()

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    is_doctor = SelectField(
        'Register as',
        choices=[('no', 'Patient'), ('yes', 'Doctor')],
        validators=[DataRequired()]
    )
    specialization = StringField('Specialization (if doctor)', validators=[Length(max=100)])  # New field
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class AvailabilityForm(FlaskForm):
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    start_time = TimeField('Start Time', format='%H:%M', validators=[DataRequired()])
    end_time = TimeField('End Time', format='%H:%M', validators=[DataRequired()])
    submit = SubmitField('Set Availability')

# Helper Functions
def send_email(subject, recipient, body):
    msg = Message(subject, sender='noreply@example.com', recipients=[recipient])
    msg.body = body
    mail.send(msg)

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        is_doctor = form.is_doctor.data.lower() == 'yes'
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            is_doctor=is_doctor,
            specialization=form.specialization.data if is_doctor else None  # Set specialization if doctor
        )
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash('Login successful!', 'success')
            return redirect(url_for('staff_dashboard' if user.is_doctor else 'dashboard'))
        else:
            flash('Login failed. Please check your credentials.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

# Patient Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_doctor:
        return redirect(url_for('staff_dashboard'))
    doctors = User.query.filter_by(is_doctor=True).all()
    appointments = current_user.appointments_as_patient
    return render_template('dashboard.html', doctors=doctors, appointments=appointments)

# Staff Dashboard
@app.route('/staff/dashboard', methods=['GET', 'POST'])
@login_required
def staff_dashboard():
    if not current_user.is_doctor:
        return redirect(url_for('dashboard'))
    form = AvailabilityForm()
    if form.validate_on_submit():
        start_time = datetime.combine(form.date.data, form.start_time.data)
        end_time = datetime.combine(form.date.data, form.end_time.data)
        overlapping_slot = Availability.query.filter(
            Availability.doctor_id == current_user.id,
            Availability.start_time < end_time,
            Availability.end_time > start_time
        ).first()
        if overlapping_slot:
            flash('This slot overlaps with an existing availability. Please choose a different time.', 'danger')
        else:
            availability = Availability(
                doctor_id=current_user.id,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(availability)
            db.session.commit()
            flash('Availability set successfully!', 'success')
    return render_template('staff_dashboard.html', form=form)

# Book Appointment
@app.route('/book/<int:doctor_id>/<int:slot_id>', methods=['POST'])
@login_required
def book_appointment(doctor_id, slot_id):
    try:
        slot = Availability.query.filter_by(id=slot_id, is_booked=False).first()
        if not slot:
            flash('This slot is already booked or no longer available. Please choose another slot.', 'danger')
        else:
            appointment = Appointment(
                doctor_id=doctor_id,
                patient_id=current_user.id,
                date=slot.start_time.date(),
                time=slot.start_time.time()
            )
            slot.is_booked = True
            db.session.add(appointment)
            db.session.commit()
            send_email(
                subject='Appointment Booked',
                recipient=current_user.email,
                body=f'Your appointment with Dr. {slot.doctor.username} is confirmed for {slot.start_time}.'
            )
            flash('Appointment booked successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while booking the appointment. Please try again later.', 'danger')
        print(f"Error: {e}")
    return redirect(url_for('dashboard'))

# Search Doctors
@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query')
    if not query:
        flash('Please enter a search term.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Search for doctors by username or specialization
    doctors = User.query.filter(
        (User.username.contains(query)) | (User.specialization.contains(query)),
        User.is_doctor == True
    ).all()
    
    return render_template('dashboard.html', doctors=doctors, appointments=current_user.appointments_as_patient)

migrate = Migrate(app, db)
# Run the Application
if __name__ == "__main__":
    app.run(debug=True)