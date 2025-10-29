import os
from math import radians, cos, sin, sqrt, atan2
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client
from dotenv import load_dotenv
load_dotenv()


# Twilio Credentials (use your real values)
# Twilio credentials from .env
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")# Your Twilio phone number

client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# --- App setup ---AA
app = Flask(__name__)
app.secret_key = "minorproject"

# --- Absolute path for database ---
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Ensure instance folder exists ---
if not os.path.exists(os.path.join(basedir, 'instance')):
    os.makedirs(os.path.join(basedir, 'instance'))

db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    location_access = db.Column(db.Boolean, default=False)
    trusted_contacts = db.Column(db.Text)  # Comma-separated contacts
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

class Community(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    skills = db.Column(db.String(200))  # e.g., First Aid, Rescue
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

# --- Utility functions ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def is_area_safe(lat, lon):
    # Placeholder: integrate with real safety API
    return True
with app.app_context():
    db.create_all()
    print("Database created successfully!")

# --- Routes ---
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        community = Community.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_type'] = 'user'
            return redirect(url_for('dashboard_user'))
        elif community and check_password_hash(community.password, password):
            session['user_id'] = community.id
            session['user_type'] = 'community'
            return redirect(url_for('dashboard_community'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

# --- Signup for normal users ---
@app.route('/signup/user', methods=['GET','POST'])
def signup_user():
    if request.method == 'POST':
        username = request.form['username']
        # Check if username exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose another.")
            return redirect(url_for('signup_user'))

        password = generate_password_hash(request.form['password'])
        full_name = request.form['full_name']
        phone = request.form['phone']
        address = request.form['address']
        location_access = 'location_access' in request.form
        contacts = request.form.getlist('trusted_contacts')
        trusted_contacts = ",".join(contacts)

        user = User(username=username, password=password, full_name=full_name,
                    phone=phone, address=address, location_access=location_access,
                    trusted_contacts=trusted_contacts)
        db.session.add(user)
        db.session.commit()
        flash("User account created successfully!")
        return redirect(url_for('login'))

    return render_template('signup_user.html')

# --- Signup for community users ---
@app.route('/signup/community', methods=['GET','POST'])
def signup_community():
    if request.method == 'POST':
        username = request.form['username']
        # Check if username exists
        if Community.query.filter_by(username=username).first():
            flash("Username already exists. Please choose another.")
            return redirect(url_for('signup_community'))

        password = generate_password_hash(request.form['password'])
        full_name = request.form['full_name']
        phone = request.form['phone']
        address = request.form['address']
        skills = request.form['skills']

        community = Community(username=username, password=password,
                              full_name=full_name, phone=phone, address=address,
                              skills=skills)
        db.session.add(community)
        db.session.commit()
        flash("Community account created successfully!")
        return redirect(url_for('login'))

    return render_template('signup_community.html')

# --- Dashboards ---
@app.route('/dashboard/user')
def dashboard_user():
    if 'user_type' in session and session['user_type'] == 'user':
        user = User.query.get(session['user_id'])
        return render_template('dashboard_user.html', user=user)
    return redirect(url_for('login'))

@app.route('/dashboard/community')
def dashboard_community():
    if 'user_type' in session and session['user_type'] == 'community':
        community = Community.query.get(session['user_id'])
        return render_template('dashboard_community.html', community=community)
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- SOS Route ---

@app.route('/sos', methods=['POST'])
def sos_alert():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get(session['user_id'])
    data = request.json
    user_lat = float(data.get('latitude'))
    user_lon = float(data.get('longitude'))  # ✅ Added this line

    # Update location
    user.latitude = user_lat
    user.longitude = user_lon
    db.session.commit()

    google_maps_url = f"https://www.google.com/maps?q={user_lat},{user_lon}"
    alert_message = (
        f"🚨 SOS Alert! {user.full_name} may be in danger.\n"
        f"Location: {google_maps_url}"
    )

    # ✅ Notify trusted contacts
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

    if user.trusted_contacts:
        contacts = user.trusted_contacts.split(',')
        for contact in contacts:
            contact = contact.strip()
            if contact:
                try:
                    client.messages.create(
                        body=alert_message,
                        from_=TWILIO_PHONE_NUMBER,  # ✅ Fixed here
                        to=contact
                    )
                except Exception as e:
                    print(f"Failed to send SMS to {contact}: {e}")
    else:
        contacts = []

    # ✅ Notify nearby Volunteers within 5 km
    volunteers = Community.query.all()
    nearby_vols = []

    for vol in volunteers:
        if vol.latitude and vol.longitude:
            distance = haversine(user_lat, user_lon, vol.latitude, vol.longitude)
            if distance <= 5:
                nearby_vols.append(vol.phone)
                try:
                    client.messages.create(
                        body=f"⚠️ Volunteer Alert! A nearby user needs help.\nLocation: {google_maps_url}",
                        from_=TWILIO_PHONE_NUMBER,  # ✅ Fixed here too
                        to=vol.phone
                    )
                except Exception as e:
                    print(f"Failed to notify volunteer {vol.phone}: {e}")

    return jsonify({
        "success": True,
        "message": "SOS sent successfully!",
        "contacts_notified": contacts,
        "volunteers_notified": nearby_vols
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database created successfully!")
    app.run(debug=True)
