from flask import Blueprint, request, jsonify
from database import Database
from models import Ride
from routes.auth_middleware import token_required
from bson import ObjectId
from datetime import datetime

ride_bp = Blueprint('ride_bp', __name__)

@ride_bp.route('/ride/create', methods=['POST'])
@token_required
def create_ride(current_user):
    data = request.get_json()
    db = Database.get_db()
    
    try:
      
        pickup_lng = float(data['pickupCoords']['lng'])
        pickup_lat = float(data['pickupCoords']['lat'])
        dropoff_lng = float(data['dropoffCoords']['lng'])
        dropoff_lat = float(data['dropoffCoords']['lat'])
        
        pickup_coords = { "type": "Point", "coordinates": [pickup_lng, pickup_lat] }
        dropoff_coords = { "type": "Point", "coordinates": [dropoff_lng, dropoff_lat] }
        
        new_ride = Ride.create_schema(
            driver_id=current_user['_id'],
            pickup=data['pickup'],
            dropoff=data['dropoff'],
            pickup_coords=pickup_coords,
            dropoff_coords=dropoff_coords,
            time=data['time'],
            seats=data['seats']
        )
        
        result = db.rides.insert_one(new_ride)
        return jsonify({"message": "Ride created", "rideId": str(result.inserted_id)}), 201
        
    except KeyError as e:
        return jsonify({"message": f"Missing field: {str(e)}"}), 400
    except ValueError:
        return jsonify({"message": "Invalid coordinates format"}), 400


@ride_bp.route('/rides/nearby', methods=['GET'])
def get_nearby_rides():
    """
    ADVANCED DB FEATURE: GeoSpatial Aggregation ($geoNear).
    - Finds rides within 'max_dist'.
    - Calculates a 'matchScore' (0-100) based on distance and availability.
    - "Smart Match Score": Closer + More Seats = Higher Score.
    """
    db = Database.get_db()
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        max_dist = float(request.args.get('dist', 5000)) # default 5km
        
       
        pipeline = [
            {
                "$geoNear": {
                    "near": { "type": "Point", "coordinates": [lng, lat] },
                    "distanceField": "distance", # Output field for distance in meters
                    "maxDistance": max_dist,
                    "spherical": True
                }
            }
        ]
        
        rides = list(db.rides.aggregate(pipeline))
        
        # Calculate Smart Match Score in Python logic
        for r in rides:
            r['_id'] = str(r['_id'])
            if 'createdAt' in r: r['createdAt'] = r['createdAt'].isoformat()
            
            # --- SCORING LOGIC ---
            # 1. Distance Score (Max 50 pts): Closer is better
            dist_val = r.get('distance', max_dist)
            # Inverse normalized distance: 1.0 at 0m, 0.0 at max_dist
            norm_dist = max(0, (max_dist - dist_val) / max_dist)
            dist_score = norm_dist * 50
            
            # 2. Seats Score (Max 50 pts): More available seats is better
            # Cap at 5 seats for max points to avoid skewing
            passengers = r.get('passengers', [])
            total_seats = int(r.get('seats', 0))
            available = max(0, total_seats - len(passengers))
            
            # 10 points per seat, max 50
            seat_score = min(available * 10, 50)
            
            # Total Score
            r['matchScore'] = int(dist_score + seat_score)
            
        # Re-sort by matchScore descending (Best matches first)
        rides.sort(key=lambda x: x['matchScore'], reverse=True)
            
        return jsonify(rides), 200
        
    except (ValueError, TypeError) as e:
        return jsonify({"message": f"Invalid parameters: {str(e)}"}), 400

@ride_bp.route('/ride/request/<ride_id>', methods=['POST'])
@token_required
def join_ride(current_user, ride_id):
    """
    ADVANCED DB FEATURE: using $push to add a passenger.
    Uses atomic update with $expr to ensure concurrency safety.
    """
    db = Database.get_db()
    user_id = str(current_user['_id'])
    
    # Check if ride exists (for 404)
    ride = db.rides.find_one({"_id": ObjectId(ride_id)})
    if not ride:
        return jsonify({"message": "Ride not found"}), 404

    # We added application-level constraints to prevent logical misuse.
    if ride['driverId'] == user_id:
        return jsonify({"message": "Driver cannot join their own ride"}), 400

    # Atomic Update combining:
    # 1. Not already joined ($ne)
    # 2. Capacity check ($expr $lt $size)
    result = db.rides.update_one(
        {
            "_id": ObjectId(ride_id),
            "passengers": { "$ne": user_id },
            "$expr": { "$lt": [{ "$size": "$passengers" }, "$seats"] }
        },
        {"$push": {"passengers": user_id}}
    )
    
    if result.modified_count > 0:
        return jsonify({"message": "Successfully joined ride"}), 200
    
    # If update failed, determine why for better UX
    # (Since we know ride exists and driver check passed)
    if user_id in ride.get('passengers', []):
        return jsonify({"message": "You already joined this ride"}), 400
    
    # If we are here, it likely means the ride is full (or became full just now)
    # Re-fetch or just assume full if concurrency high
    updated_ride = db.rides.find_one({"_id": ObjectId(ride_id)})
    if len(updated_ride.get('passengers', [])) >= updated_ride['seats']:
        return jsonify({"message": "Ride is full"}), 400
        
    return jsonify({"message": "Join failed"}), 400


# ==========================================
# NEW API ENDPOINTS (v1) - Advanced Features
# ==========================================

@ride_bp.route('/rides/search', methods=['GET'])
@token_required
def search_rides_v1(current_user):
    """
    1) SEARCH RIDES
    GET /api/v1/rides/search?from=<pickup>&to=<dropoff>
    - Filters rides using the compound index on 'pickup' and 'dropoff' (text regex).
    - Returns JSON list of matches.
    """
    db = Database.get_db()
    pickup_query = request.args.get('from')
    dropoff_query = request.args.get('to')

    # Build query
    query = {}
    if pickup_query:
        # Case-insensitive regex search
        query['pickup'] = {"$regex": pickup_query, "$options": "i"}
    if dropoff_query:
        query['dropoff'] = {"$regex": dropoff_query, "$options": "i"}

    try:
        # Use projection to limit fields if necessary, here we return full objects
        rides = list(db.rides.find(query).limit(50))
        
        # Serialize ObjectId and datetime
        for r in rides:
            r['_id'] = str(r['_id'])
            if 'createdAt' in r: r['createdAt'] = r['createdAt'].isoformat()
            
        return jsonify(rides), 200
    except Exception as e:
        return jsonify({"message": "Error searching rides", "error": str(e)}), 500

@ride_bp.route('/my/joined-rides', methods=['GET'])
@token_required
def my_joined_rides(current_user):
    """
    2) MY JOINED RIDES
    GET /api/v1/my/joined-rides
    - Finds rides where the current user's ID is in the 'passengers' array.
    - Demonstrates array querying in MongoDB.
    """
    db = Database.get_db()
    user_id = str(current_user['_id'])

    try:
        # Query: find docs where 'passengers' array contains 'user_id'
        rides = list(db.rides.find({"passengers": user_id}))
        
        for r in rides:
            r['_id'] = str(r['_id'])
            if 'createdAt' in r: r['createdAt'] = r['createdAt'].isoformat()

        return jsonify(rides), 200
    except Exception as e:
        return jsonify({"message": "Error fetching joined rides", "error": str(e)}), 500

@ride_bp.route('/ride/cancel/<ride_id>', methods=['POST'])
@token_required
def cancel_ride_request(current_user, ride_id):
    """
    3) CANCEL RIDE REQUEST
    POST /api/v1/ride/cancel/<ride_id>
    - Removes the user from the 'passengers' array using $pull.
    - Ensures atomicity.
    """
    db = Database.get_db()
    user_id = str(current_user['_id'])

    try:
        # Check if ride exists
        ride = db.rides.find_one({"_id": ObjectId(ride_id)})
        if not ride:
            return jsonify({"message": "Ride not found"}), 404
        
        # Check if user is actually a passenger
        if user_id not in ride.get('passengers', []):
            return jsonify({"message": "You are not a passenger in this ride"}), 400

        # Atomic Update: $pull
        # Removes all instances of user_id from the passengers array
        result = db.rides.update_one(
            {"_id": ObjectId(ride_id)},
            {"$pull": {"passengers": user_id}}
        )

        if result.modified_count > 0:
            return jsonify({"message": "Successfully cancelled ride request"}), 200
        else:
            return jsonify({"message": "Cancellation failed"}), 500

    except Exception as e:
        return jsonify({"message": "Error cancelling ride", "error": str(e)}), 500

@ride_bp.route('/driver/stats', methods=['GET'])
@token_required
def driver_stats_v1(current_user):
    """
    4) DRIVER STATISTICS (AGGREGATION)
    GET /api/v1/driver/stats
    - Calculates stats for the LOGGED-IN driver.
    - Uses MongoDB Aggregation Pipeline: $match, $project (size), $group.
    """
    db = Database.get_db()
    driver_id = str(current_user['_id'])

    pipeline = [
        # 1. Match rides created by this driver
        { "$match": { "driverId": driver_id } },

        # 2. Project existing fields plus the count of passengers
        { "$project": {
            "seats": 1,
            "passengerCount": { "$size": "$passengers" }
        }},

        # 3. Group to calculate totals and averages
        { "$group": {
            "_id": "$driverId", # or null since we matched one driver
            "totalRidesOffered": { "$sum": 1 },
            "totalPassengersCarried": { "$sum": "$passengerCount" },
            "averagePassengersPerRide": { "$avg": "$passengerCount" }
        }}
    ]

    try:
        stats = list(db.rides.aggregate(pipeline))
        
        if not stats:
            return jsonify({
                "totalRidesOffered": 0,
                "totalPassengersCarried": 0,
                "averagePassengersPerRide": 0
            }), 200

        result = stats[0]
        # Cleanup _id from result if present
        if "_id" in result: del result["_id"]
        
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": "Error calculating stats", "error": str(e)}), 500

@ride_bp.route('/ride/<ride_id>/availability', methods=['GET'])
@token_required
def ride_availability(current_user, ride_id):
    """
    5) RIDE AVAILABILITY
    GET /api/v1/ride/<ride_id>/availability
    - Returns remaining seats and status.
    - Logic: seats - length(passengers).
    """
    db = Database.get_db()

    try:
        ride = db.rides.find_one({"_id": ObjectId(ride_id)})
        if not ride:
            return jsonify({"message": "Ride not found"}), 404

        total_seats = ride.get('seats', 0)
        taken_seats = len(ride.get('passengers', []))
        remaining = total_seats - taken_seats
        
        status = "Available" if remaining > 0 else "Full"

        return jsonify({
            "rideId": str(ride['_id']),
            "totalSeats": total_seats,
            "seatsTaken": taken_seats,
            "remainingSeats": remaining,
            "status": status
        }), 200

    except Exception as e:
        return jsonify({"message": "Error checking availability", "error": str(e)}), 500

@ride_bp.route('/analytics/popular-routes', methods=['GET'])
@token_required
def popular_routes(current_user):
    """
    6) POPULAR ROUTES ANALYTICS
    GET /api/v1/analytics/popular-routes
    - Groups rides by pickup -> dropoff.
    - Returns top 5 frequent routes.
    """
    db = Database.get_db()
    
    pipeline = [
        {
            "$group": {
                "_id": { "from": "$pickup", "to": "$dropoff" },
                "rideCount": { "$sum": 1 }
            }
        },
        { "$sort": { "rideCount": -1 } },
        { "$limit": 5 }
    ]
    
    try:
        results = list(db.rides.aggregate(pipeline))
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"message": "Error fetching analytics", "error": str(e)}), 500
