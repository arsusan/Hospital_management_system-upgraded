from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField,
    DateField, TimeField, BooleanField, SelectField
)
from wtforms.validators import DataRequired, Length, Email, EqualTo
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email
class RegistrationForm(FlaskForm):
    username = StringField(
        'Username', 
        validators=[DataRequired(), Length(min=3, max=20)]
    )
    email = StringField(
        'Email', 
        validators=[DataRequired(), Email()]
    )
    password = PasswordField(
        'Password', 
        validators=[DataRequired(), Length(min=6, max=20)]
    )
    confirm_password = PasswordField(
        'Confirm Password', 
        validators=[DataRequired(), EqualTo('password', message="Passwords must match.")]
    )
    submit = SubmitField('Create Account')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class StaffLoginForm(FlaskForm):
    staff_id = StringField('Staff ID', validators=[DataRequired()])  # Changed to username to match User model
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Staff Login')

class AvailabilityForm(FlaskForm):
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    start_time = TimeField('Start Time', format='%H:%M', validators=[DataRequired()])
    end_time = TimeField('End Time', format='%H:%M', validators=[DataRequired()])
    submit = SubmitField('Set Availability')