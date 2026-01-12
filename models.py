from datetime import datetime, timezone

class User:
    @staticmethod
    def create_schema(name, email, password_hash, gender, phone):
        return {
            "name": name,
            "email": email,
            "password": password_hash,
            "gender": gender,
            "phone": phone,
            "createdAt": datetime.now(timezone.utc)
        }

class Ride:
    @staticmethod
    def create_schema(driver_id, pickup, dropoff, pickup_coords, dropoff_coords, time, seats):
        """
        Constructs the Ride document.
        ensure pickup_coords and dropoff_coords are in GeoJSON format:
        { "type": "Point", "coordinates": [longitude, latitude] }
        """
        return {
            "driverId": str(driver_id),
            "pickup": pickup,
            "dropoff": dropoff,
            "pickupCoords": pickup_coords,
            "dropoffCoords": dropoff_coords,
            "time": time,
            "seats": int(seats),
            "passengers": [],  # Will store list of user IDs
            "createdAt": datetime.now(timezone.utc)
        }
