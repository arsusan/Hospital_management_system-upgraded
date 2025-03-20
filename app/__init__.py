from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from config import Config

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'routes.login'  # Update the login view
mail = Mail()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__, template_folder='C:/Users/aryal/Desktop/HMS/templates', static_folder= 'C:/Users/aryal/Desktop/HMS/static')  # Ensure the correct template folder
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # Register the user_loader function
    from app.models import User  # Import the User model

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    from .models import User, Appointment, Availability
    from .admin import init_admin
    init_admin(app, db) 
    # Register routes
    from app.routes import routes
    app.register_blueprint(routes)

    return app