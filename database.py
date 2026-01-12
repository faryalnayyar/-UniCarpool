from pymongo import MongoClient, GEOSPHERE, ASCENDING, DESCENDING
from config import Config

class Database:
    client = None
    db = None

    @staticmethod
    def initialize():
        if Database.db is not None:
            return Database.db

        try:
            if not Config.MONGO_URI:
                print("CRITICAL: MONGO_URI is not set in environment variables!")
                return None

            Database.client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
            # Test connection
            Database.client.admin.command('ping')
            
            Database.db = Database.client.get_database()
            print("Connected to MongoDB successfully!")
            Database.create_indexes()
            return Database.db
        except Exception as e:
            print(f"Error connecting to MongoDB: {str(e)}")
            Database.db = None
            return None

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
        if Database.db is None:
            return Database.initialize()
        return Database.db
