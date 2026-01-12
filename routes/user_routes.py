from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from database import Database
from models import User
from routes.auth_middleware import token_required
from bson import ObjectId

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    db = Database.get_db()
    
    if db is None:
        return jsonify({"message": "Database connection failed. Check MONGO_URI and IP whitelist."}), 500
    
    # Check if user exists
    if db.users.find_one({"email": data['email']}):
        return jsonify({"message": "User already exists"}), 400
    
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    
    new_user = User.create_schema(
        name=data['name'],
        email=data['email'],
        password_hash=hashed_password,
        gender=data.get('gender', 'Other'),
        phone=data.get('phone', '')
    )
    
    result = db.users.insert_one(new_user)
    
    return jsonify({"message": "User registered successfully", "userId": str(result.inserted_id)}), 201

@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    db = Database.get_db()
    
    if db is None:
        return jsonify({"message": "Database connection failed. Check MONGO_URI and IP whitelist."}), 500
    
    user = db.users.find_one({"email": data['email']})
    
    if not user or not check_password_hash(user['password'], data['password']):
        return jsonify({"message": "Invalid credentials"}), 401
    
    # Generate JWT
    token = jwt.encode({
        'user_id': str(user['_id']),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, current_app.config['SECRET_KEY'], algorithm="HS256")
    
    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {
            "name": user['name'],
            "email": user['email'],
            "_id": str(user['_id'])
        }
    }), 200

@user_bp.route('/me', methods=['GET'])
@token_required
def get_me(current_user):
    user_data = {
        "_id": str(current_user['_id']),
        "name": current_user['name'],
        "email": current_user['email'],
        "gender": current_user.get('gender'),
        "phone": current_user.get('phone')
    }
    return jsonify(user_data), 200

@user_bp.route('/my/rides', methods=['GET'])
@token_required
def get_my_rides(current_user):
    db = Database.get_db()
    
    # Rides where user is driver
    driver_rides = list(db.rides.find({"driverId": str(current_user['_id'])}))
    
    # Rides where user is a passenger
    passenger_rides = list(db.rides.find({"passengers": str(current_user['_id'])}))
    
    # Helper to serialize ObjectId
    def serialize_rides(rides):
        for r in rides:
            r['_id'] = str(r['_id'])
            # Format datetime if needed
            if 'createdAt' in r:
                r['createdAt'] = r['createdAt'].isoformat()
        return rides
        
    return jsonify({
        "driven_rides": serialize_rides(driver_rides),
        "joined_rides": serialize_rides(passenger_rides)
    }), 200
