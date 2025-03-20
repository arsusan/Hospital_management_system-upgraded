from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from .models import User, Appointment, Availability


# Optional: Customizing views if needed

class UserModelView(ModelView):
    column_list = ['id', 'username', 'email', 'years_of_working']
    form_columns = ['username', 'email', 'password', 'years_of_working']
    
class AvailabilityModelView(ModelView):
    column_list = ['doctor', 'start_time', 'end_time', 'is_booked']

class AppointmentModelView(ModelView):
    column_list = ['doctor', 'patient', 'date', 'time', 'status']

def init_admin(app, db):
    from flask_admin import Admin
    admin = Admin(app, name='HMS Admin', template_mode='bootstrap3')
    
    admin.add_view(UserModelView(User, db.session))
    admin.add_view(AvailabilityModelView(Availability, db.session))
    admin.add_view(AppointmentModelView(Appointment, db.session))
