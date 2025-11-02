import os
from math import radians, cos, sin, sqrt, atan2
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Twilio Credentials (use your real values in .env)
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# --- App setup ---
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "minorproject")

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
    trusted_contacts = db.Column(db.Text)  # Comma-separated contacts (E.164 format recommended)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

class Volunteer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    service_radius = db.Column(db.Float, default=5.0)  # default 5 km range
    is_active = db.Column(db.Boolean, default=True)

# --- Utility functions ---
def haversine(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float("inf")
    R = 6371  # km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def is_area_safe(lat, lon):
    # Placeholder: integrate with real safety API if needed
    return True

with app.app_context():
    db.create_all()
    print("Database created successfully!")

# --- Routes ---
@app.route('/')
def index():
    return redirect(url_for('login'))

# --------------------
# Authentication
# --------------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['username']
        password = request.form['password']

        # Try user login first
        user = User.query.filter_by(username=username_or_email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_type'] = 'user'
            return redirect(url_for('dashboard_user'))

        # Try volunteer login (by username or email)
        volunteer = Volunteer.query.filter(
            (Volunteer.username == username_or_email) | (Volunteer.email == username_or_email)
        ).first()
        if volunteer and check_password_hash(volunteer.password, password):
            session['user_id'] = volunteer.id
            session['user_type'] = 'volunteer'
            return redirect(url_for('dashboard_volunteer'))

        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

# --- Signup for normal users ---
@app.route('/signup/user', methods=['GET','POST'])
def signup_user():
    if request.method == 'POST':
        username = request.form['username']
        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose another.")
            return redirect(url_for('signup_user'))

        password = generate_password_hash(request.form['password'])
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        location_access = 'location_access' in request.form
        contacts = request.form.getlist('trusted_contacts')
        trusted_contacts = ",".join([c.strip() for c in contacts if c.strip()])

        user = User(username=username, password=password, full_name=full_name,
                    phone=phone, address=address, location_access=location_access,
                    trusted_contacts=trusted_contacts)
        db.session.add(user)
        db.session.commit()
        flash("User account created successfully!")
        return redirect(url_for('login'))
    return render_template('signup_user.html')

# --- Volunteer Signup & Login ---
@app.route('/volunteer/signup', methods=['GET','POST'])
def volunteer_signup():
    if request.method == 'POST':
        username = request.form.get('username') or None
        email = request.form.get('email') or None
        if username and Volunteer.query.filter_by(username=username).first():
            flash("Username already exists. Please choose another.")
            return redirect(url_for('volunteer_signup'))
        if email and Volunteer.query.filter_by(email=email).first():
            flash("Email already exists. Please choose another.")
            return redirect(url_for('volunteer_signup'))

        password = generate_password_hash(request.form['password'])
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        service_radius = float(request.form.get('service_radius', 5.0))

        volunteer = Volunteer(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            phone=phone,
            address=address,
            service_radius=service_radius
        )
        db.session.add(volunteer)
        db.session.commit()
        flash("Volunteer account created successfully! Please log in.")
        return redirect(url_for('login'))
    return render_template('volunteer_signup.html')

@app.route('/volunteer/login', methods=['GET','POST'])
def volunteer_login():
    # Optional dedicated volunteer login page; main /login also supports volunteers
    if request.method == 'POST':
        username_or_email = request.form['username']
        password = request.form['password']
        volunteer = Volunteer.query.filter(
            (Volunteer.username == username_or_email) | (Volunteer.email == username_or_email)
        ).first()
        if volunteer and check_password_hash(volunteer.password, password):
            session['user_id'] = volunteer.id
            session['user_type'] = 'volunteer'
            return redirect(url_for('dashboard_volunteer'))
        return render_template('volunteer_login.html', error="Invalid credentials")
    return render_template('volunteer_login.html')

# --- Dashboards ---
@app.route('/dashboard/user')
def dashboard_user():
    if 'user_type' in session and session['user_type'] == 'user':
        user = User.query.get(session['user_id'])
        return render_template('dashboard_user.html', user=user)
    return redirect(url_for('login'))

@app.route('/dashboard/volunteer')
@app.route('/dashboard/community')  # keep old name working
def dashboard_volunteer():
    if 'user_type' in session and session['user_type'] == 'volunteer':
        volunteer = Volunteer.query.get(session['user_id'])
        return render_template('dashboard_community.html', community=volunteer)
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- SOS Route ---
@app.route('/sos', methods=['POST'])
def sos_alert():
    if 'user_id' not in session or session.get('user_type') != 'user':
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get(session['user_id'])
    data = request.json or {}
    try:
        user_lat = float(data.get('latitude'))
        user_lon = float(data.get('longitude'))
    except Exception:
        return jsonify({"error": "Invalid coordinates"}), 400

    print("📍 Received SOS location:", user_lat, user_lon)

    # Update location
    user.latitude = user_lat
    user.longitude = user_lon
    db.session.commit()

    # Encoded comma for clickable Google Maps link in SMS clients
    google_maps_url = f"https://maps.google.com/?q={user_lat}%2C{user_lon}"

    # Create alert message
    alert_message = (
        f"🚨 SOS Alert! {user.full_name or user.username} may be in danger.\n"
        f"Location: {google_maps_url}"
    )

    # Notify trusted contacts
    TWILIO_PHONE_NUMBER = TWILIO_PHONE_NUMBER  # from environment
    if user.trusted_contacts:
        contacts = [c.strip() for c in user.trusted_contacts.split(',') if c.strip()]
        for contact in contacts:
            try:
                client.messages.create(
                    body=alert_message,
                    from_=TWILIO_PHONE_NUMBER,
                    to=contact
                )
            except Exception as e:
                print(f"Failed to send SMS to {contact}: {e}")
    else:
        contacts = []

    # Notify nearby Volunteers within their service radius
    volunteers = Volunteer.query.filter_by(is_active=True).all()
    nearby_vols = []
    for vol in volunteers:
        if vol.latitude is not None and vol.longitude is not None:
            distance = haversine(user_lat, user_lon, vol.latitude, vol.longitude)
            if distance <= (vol.service_radius or 5.0):
                nearby_vols.append(vol.phone)
                try:
                    client.messages.create(
                        body=f"⚠️ Volunteer Alert! A nearby user needs help.\nLocation: {google_maps_url}",
                        from_=TWILIO_PHONE_NUMBER,
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

# Update volunteer live location
@app.route('/update_vol_location', methods=['POST'])
def update_vol_location():
    if 'user_type' in session and session['user_type'] == 'volunteer':
        data = request.json or {}
        volunteer = Volunteer.query.get(session['user_id'])
        try:
            volunteer.latitude = float(data.get('latitude'))
            volunteer.longitude = float(data.get('longitude'))
        except Exception:
            # ignore if invalid, but you can return 400 if you want
            pass
        db.session.commit()
        return jsonify({"status": "updated"})
    return jsonify({"error": "Unauthorized"}), 401

# Get nearby volunteers for the active user
@app.route('/get_nearby_vols')
def get_nearby_vols():
    if 'user_id' not in session or session.get('user_type') != 'user':
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get(session['user_id'])
    if user.latitude is None or user.longitude is None:
        return jsonify([])

    volunteers = Volunteer.query.filter_by(is_active=True).all()
    nearby = []
    for vol in volunteers:
        if vol.latitude is not None and vol.longitude is not None:
            dist = haversine(user.latitude, user.longitude, vol.latitude, vol.longitude)
            if dist <= (vol.service_radius or 5.0):
                nearby.append({
                    "name": vol.full_name,
                    "phone": vol.phone,
                    "lat": vol.latitude,
                    "lon": vol.longitude,
                    "distance_km": round(dist, 2)
                })
    return jsonify(nearby)

# Fetch Active SOS Users for Volunteers
@app.route('/get_active_sos')
def get_active_sos():
    sos_users = User.query.filter(User.latitude.isnot(None), User.longitude.isnot(None)).all()
    data = []
    for u in sos_users:
        data.append({
            "name": u.full_name or u.username,
            "phone": u.phone,
            "lat": u.latitude,
            "lon": u.longitude
        })
    return jsonify(data)

# Optional: volunteer respond endpoint (mark as responding)
@app.route('/volunteer/respond', methods=['POST'])
def volunteer_respond():
    if 'user_type' in session and session['user_type'] == 'volunteer':
        data = request.json or {}
        user_phone = data.get('user_phone')
        # You can implement logic to mark response/notify user that a volunteer is responding.
        # For now just return success.
        return jsonify({"success": True, "message": "Marked as responding", "user_phone": user_phone})
    return jsonify({"error": "Unauthorized"}), 401

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database created successfully!")
    app.run(debug=True)
