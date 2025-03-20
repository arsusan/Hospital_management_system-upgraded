from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt, mail
from app.models import User, Availability, Appointment
from app.forms import RegistrationForm, LoginForm, AvailabilityForm, StaffLoginForm
from datetime import datetime, timedelta
import traceback
import json
from flask_mail import Message
from sqlalchemy import or_, and_
from werkzeug.security import check_password_hash
from functools import wraps

routes = Blueprint('routes', __name__)

# --------------------------
# Helper Functions
# --------------------------

def send_email(subject, recipient, body):
    try:
        msg = Message(subject, sender='noreply@example.com', recipients=[recipient])
        msg.body = body
        mail.send(msg)
    except Exception as e:
        print(f"Email error: {str(e)}")

def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.email.endswith('@ar.com'):
            flash('Staff access required', 'danger')
            return redirect(url_for('routes.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --------------------------
# Core Routes
# --------------------------

@routes.route('/')
def home():
    return render_template('home.html')

@routes.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Proper password hashing
            hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            
            new_user = User(
                username=form.username.data,
                email=form.email.data,
                password=hashed_pw,  # Use the hashed password
                years_of_working=0
            )
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful!", "success")
            return redirect(url_for('routes.login'))

        except Exception as e:
            db.session.rollback()
            flash("Registration failed", "danger")
    
    return render_template('register.html', form=form)

@routes.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            if user.email.endswith('@ar.com'):
                flash('Staff members must use staff login', 'warning')
                return redirect(url_for('routes.staff_login'))
            
            login_user(user)
            return redirect(url_for('routes.dashboard'))
        
        flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)

@routes.route('/staff_login', methods=['GET', 'POST'])
def staff_login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.staff_dashboard'))

    form = StaffLoginForm()
    if form.validate_on_submit():
        staff = User.query.filter_by(username=form.staff_id.data).first()

        if staff and bcrypt.check_password_hash(staff.password, form.password.data):
            if not staff.email.endswith('@ar.com'):
                flash('Invalid staff credentials', 'danger')
                return redirect(url_for('routes.staff_login'))
            
            login_user(staff)
            return redirect(url_for('routes.staff_dashboard'))
        
        flash('Invalid staff credentials', 'danger')
    return render_template('login.html', form=form)

@routes.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('routes.login'))

# --------------------------
# Dashboard Routes
# --------------------------
from datetime import datetime
@routes.route('/dashboard')
@login_required
def dashboard():
    current_time = datetime.utcnow()
    
    # Get doctors with available future slots
    doctors = User.query.join(Availability).filter(
        User.email.endswith('@ar.com'),
        Availability.is_booked == False,
        Availability.start_time > current_time
    ).distinct().all()
    
    appointments = current_user.appointments_as_patient
    
    return render_template('dashboard.html',
                         doctors=doctors,
                         appointments=appointments,
                         current_time=current_time,
                         datetime=datetime)

@routes.route('/staff/dashboard', methods=['GET', 'POST'])
@login_required
@doctor_required
def staff_dashboard():
    form = AvailabilityForm()
    
    if form.validate_on_submit():
        try:
            start_time = datetime.combine(form.date.data, form.start_time.data)
            end_time = datetime.combine(form.date.data, form.end_time.data)
            
            overlapping = Availability.query.filter(
                Availability.doctor_id == current_user.id,
                Availability.start_time < end_time,
                Availability.end_time > start_time
            ).first()
            
            if overlapping:
                flash('Slot overlap error', 'danger')
            else:
                new_slot = Availability(
                    doctor_id=current_user.id,
                    start_time=start_time,
                    end_time=end_time
                )
                db.session.add(new_slot)
                db.session.commit()
                flash('Availability added', 'success')
        except Exception as e:
            db.session.rollback()
            print(f"Availability error: {str(e)}")
    
    return render_template('staff_dashboard.html', form=form)

# --------------------------
# Availability Management
# --------------------------

@routes.route('/set_availability', methods=['POST'])
@login_required
@doctor_required
def set_availability():
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = request.form.get('availability')
            if not data:
                return jsonify({
                    "success": False,
                    "error": "No availability data provided"
                })

            slots = json.loads(data)
            
            # Clear existing availability
            Availability.query.filter_by(doctor_id=current_user.id).delete()
            
            # Add new slots
            for slot in slots:
                new_slot = Availability(
                    doctor_id=current_user.id,
                    start_time=datetime.fromisoformat(slot['start']),
                    end_time=datetime.fromisoformat(slot['end'])
                )
                db.session.add(new_slot)
            
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "Availability saved successfully"
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    # Handle regular form submissions
    try:
        # Add manual availability entry logic here if needed
        flash("Availability saved successfully", "success")
        return redirect(url_for('routes.staff_dashboard'))

    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('routes.staff_dashboard'))

# --------------------------
# Appointment Routes
# --------------------------

@routes.route('/book/<int:doctor_id>/<int:slot_id>', methods=['POST'])
@login_required
def book_appointment(doctor_id, slot_id):
    try:
        slot = Availability.query.filter_by(
            id=slot_id,
            doctor_id=doctor_id,
            is_booked=False
        ).first_or_404()
        
        if slot.start_time < datetime.now():
            flash('Expired slot', 'danger')
            return redirect(url_for('routes.dashboard'))
        
        appointment = Appointment(
            doctor_id=doctor_id,
            patient_id=current_user.id,
            date=slot.start_time.date(),
            time=slot.start_time.time(),
            status='Scheduled'
        )
        
        slot.is_booked = True
        db.session.add(appointment)
        db.session.commit()
        
        send_email(
            'Appointment Confirmed',
            current_user.email,
            f'Appointment booked for {slot.start_time}'
        )
        
        flash('Booking successful', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Booking error: {str(e)}")
    
    return redirect(url_for('routes.dashboard'))

# --------------------------
# Additional Routes
# --------------------------

@routes.route('/search')
@login_required
def search():
    current_time = datetime.utcnow()
    query = request.args.get('q', '').strip().lower()
    
    # Get matching doctors with available slots
    doctors = User.query.filter(
        User.email.endswith('@ar.com'),
        or_(
            User.username.ilike(f'%{query}%')
        )
    ).outerjoin(Availability).filter(
        (Availability.is_booked == False) | (Availability.id.is_(None)),
        (Availability.start_time > current_time) | (Availability.id.is_(None))
    ).distinct().all()
    
    appointments = current_user.appointments_as_patient
    
    return render_template('dashboard.html',
                         doctors=doctors,
                         appointments=appointments,
                         current_time=current_time,
                         datetime=datetime,
                         search_query=query)

@routes.route('/get_booked_slots')
@login_required
@doctor_required
def get_booked_slots():
    try:
        slots = Availability.query.filter_by(
            doctor_id=current_user.id,
            is_booked=True
        ).all()
        return jsonify([{
            "title": "Booked",
            "start": slot.start_time.isoformat(),
            "end": slot.end_time.isoformat()
        } for slot in slots])
    except Exception as e:
        return jsonify([])

@routes.route('/login-choice')
def login_choice():
    return render_template('login_choice.html')