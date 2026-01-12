import random
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash
from database import Database
from config import Config
from pymongo import MongoClient
import time

# Use coordinates near the default frontend map view (Manhattan)
# Default keys in rides.js: Lat 40.75, Lng -73.98
CENTER_LAT = 40.75
CENTER_LNG = -73.98

def seed():
    print("🌱 Seeding Demo Data...")
    
    # Initialize DB connection manually to avoid app context issues if not needed
    client = MongoClient(Config.MONGO_URI)
    db = client.get_database()
    
    # 1. Clear existing data (Optional: comment out if you want to keep)
    print("   - Clearing existing users and rides...")
    db.users.delete_many({})
    db.rides.delete_many({})
    
    # 2. Create Users
    print("   - Creating Users...")
    users_data = [
        {"name": "Demo Driver", "email": "driver@test.com", "gender": "Male"},
        {"name": "Alice Passenger", "email": "alice@test.com", "gender": "Female"},
        {"name": "Bob Student", "email": "bob@test.com", "gender": "Male"},
        {"name": "Sarah Commuter", "email": "sarah@test.com", "gender": "Female"},
    ]
    
    created_users = []
    for u in users_data:
        user_doc = {
            "name": u['name'],
            "email": u['email'],
            "password": generate_password_hash("password", method='pbkdf2:sha256'),
            "gender": u['gender'],
            "phone": "1234567890",
            "createdAt": datetime.now(timezone.utc)
        }
        res = db.users.insert_one(user_doc)
        created_users.append({**user_doc, "_id": res.inserted_id})
        
    driver = created_users[0]
    alice = created_users[1]
    bob = created_users[2]
    sarah = created_users[3]
    
    print(f"     -> Created {len(created_users)} users. Password for all: 'password'")
    
    # 3. Create Rides
    print("   - Creating Rides...")
    
    # Helper to clean coords
    def get_coords(lat_offset, lng_offset):
        return {
            "type": "Point",
            "coordinates": [CENTER_LNG + lng_offset, CENTER_LAT + lat_offset]
        }
        
    rides_data = [
        # Ride 1: Nearby, High Match (Close + Seats)
        {
            "driverId": str(driver['_id']),
            "pickup": "University Library",
            "dropoff": "Grand Central Station",
            "pickupCoords": get_coords(0.002, 0.002), # Very close
            "dropoffCoords": get_coords(0.05, 0.05),
            "time": (datetime.now() + timedelta(hours=2)).isoformat(),
            "seats": 4,
            "passengers": [str(alice['_id'])] # 1 seat taken
        },
        # Ride 2: Nearby, Low Match (Full)
        {
            "driverId": str(sarah['_id']),
            "pickup": "Campus Gate 1",
            "dropoff": "Downtown Mall",
            "pickupCoords": get_coords(-0.002, -0.002), # Close
            "dropoffCoords": get_coords(-0.06, -0.06),
            "time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "seats": 3,
            "passengers": [str(driver['_id']), str(bob['_id']), str(alice['_id'])] # Full
        },
        # Ride 3: Far away
        {
            "driverId": str(bob['_id']),
            "pickup": "North Campus Housing",
            "dropoff": "Airport",
            "pickupCoords": get_coords(0.1, 0.1), # ~10km away
            "dropoffCoords": get_coords(0.2, 0.2),
            "time": (datetime.now() + timedelta(days=1)).isoformat(),
            "seats": 2,
            "passengers": []
        },
        # Ride 4: Popular Route Logic (Same route as Ride 1)
        {
            "driverId": str(sarah['_id']),
            "pickup": "University Library",
            "dropoff": "Grand Central Station",
            "pickupCoords": get_coords(0.003, 0.003),
            "dropoffCoords": get_coords(0.05, 0.05),
            "time": (datetime.now() + timedelta(hours=5)).isoformat(),
            "seats": 3,
            "passengers": []
        },
         # Ride 5: Another Popular Route
        {
            "driverId": str(driver['_id']),
            "pickup": "Science Block",
            "dropoff": "City Center",
            "pickupCoords": get_coords(0.005, -0.005),
            "dropoffCoords": get_coords(0.1, 0.1),
            "time": (datetime.now() + timedelta(hours=3)).isoformat(),
            "seats": 3,
            "passengers": [str(bob['_id'])]
        }
    ]
    
    db.rides.insert_many(rides_data)
    print(f"     -> Created {len(rides_data)} rides.")

    print("\n✅ SEEDING COMPLETE!")
    print("------------------------------------------------")
    print("Log in with:")
    print(f"  Email: {driver['email']}")
    print("  Password: password")
    print("------------------------------------------------")

if __name__ == "__main__":
    seed()
