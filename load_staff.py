import json
from app import create_app, db
from app.models import User
from flask_bcrypt import Bcrypt

def load_staff_data(json_file):
    # Create the Flask app
    app = create_app()
    with app.app_context():
        bcrypt = Bcrypt(app)

        # Load JSON data
        with open(json_file, 'r') as file:
            staff_data = json.load(file)

        # Insert staff data into the database
        for staff in staff_data:
            # Hash the password
            hashed_password = bcrypt.generate_password_hash(staff.get('password', 'default_password')).decode('utf-8')
            
            # Create a new user with default values for missing fields
            user = User(
                username=staff.get('username', 'default_username'),
                email=staff.get('email', 'default@ar.com'),
                password=hashed_password,
                years_of_working=staff.get('years_of_working', 0)
            )
            db.session.add(user)
        
        # Commit changes to the database
        db.session.commit()
        print("Staff data loaded successfully!")

if __name__ == "__main__":
    # Path to the JSON file
    json_file = "staff_data.json"
    load_staff_data(json_file)