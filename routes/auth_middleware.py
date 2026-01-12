import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app
from database import Database
from bson import ObjectId

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check for Authorization header: Bearer <token>
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            db = Database.get_db()
            current_user = db.users.find_one({"_id": ObjectId(data['user_id'])})
            if not current_user:
                raise Exception("User not found")
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401

        return f(current_user, *args, **kwargs)

    return decorated
