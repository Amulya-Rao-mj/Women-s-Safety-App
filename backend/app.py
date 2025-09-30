from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

# --- Database Config ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///safety_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)

# --- Routes ---
@app.route("/")
def home():
    return jsonify({"message": "Women’s Safety App Backend Running 🚀"})

# --- User Signup ---
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 400

    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201

# --- User Login ---
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        return jsonify({"message": "Login successful", "user_id": user.id})
    else:
        return jsonify({"message": "Invalid credentials"}), 401

# --- Add Trusted Contact ---
@app.route("/contacts", methods=["POST"])
def add_contact():
    data = request.json
    user_id = data.get("user_id")
    name = data.get("name")
    phone = data.get("phone")

    new_contact = Contact(user_id=user_id, name=name, phone=phone)
    db.session.add(new_contact)
    db.session.commit()

    return jsonify({"message": "Contact added successfully"})

# --- List Contacts ---
@app.route("/contacts/<int:user_id>", methods=["GET"])
def list_contacts(user_id):
    contacts = Contact.query.filter_by(user_id=user_id).all()
    result = [{"id": c.id, "name": c.name, "phone": c.phone} for c in contacts]
    return jsonify(result)

# --- Fake Anomaly Detection ---
def detect_anomaly(data):
    hr = data.get("heartbeat", 80)
    acc = data.get("acceleration", 0)
    if hr > 160 or hr < 45:
        return {"alert": True, "reason": "Abnormal heartbeat"}
    if acc > 25:
        return {"alert": True, "reason": "Fall detected"}
    return {"alert": False, "reason": "Normal"}

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    result = detect_anomaly(data)
    return jsonify(result)

# --- Run App ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # create tables if they don't exist
    app.run(debug=True)
