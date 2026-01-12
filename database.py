from pymongo import MongoClient, GEOSPHERE, ASCENDING, DESCENDING
from config import Config

class Database:
    client = None
    db = None

    @staticmethod
    def initialize():
        try:
            Database.client = MongoClient(Config.MONGO_URI)
            Database.db = Database.client.get_database()
            print("Connected to MongoDB successfully!")
            Database.create_indexes()
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")

    @staticmethod
    def create_indexes():
     
        if Database.db is None:
            return

        # USERS COLLECTION
        users = Database.db.users
        users.create_index([("email", ASCENDING)], unique=True)
        print("Index created: users -> email (unique)")

        # RIDES COLLECTION
        rides = Database.db.rides
        
        # GeoSpatial Index for location-based search
        # Must use 2dsphere for GeoJSON points
        rides.create_index([("pickupCoords", GEOSPHERE)])
        print("Index created: rides -> pickupCoords (2dsphere)")

        # Compound index for route filtering
        rides.create_index([("pickup", ASCENDING), ("dropoff", ASCENDING)])
        print("Index created: rides -> pickup + dropoff")

    @staticmethod
    def get_db():
        return Database.db
