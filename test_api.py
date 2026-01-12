import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def log(msg, type="INFO"):
    print(f"[{type}] {msg}")

def get_auth_token(email, password, name="Test User"):
    # Try login first
    login_payload = {"email": email, "password": password}
    res = requests.post(f"{BASE_URL}/api/login", json=login_payload)
    
    if res.status_code == 200:
        return res.json()['token']
    elif res.status_code == 401:
        # If login fails, try register
        log(f"Registering user {email}...", "SETUP")
        reg_payload = {
            "name": name, 
            "email": email, 
            "password": password, 
            "gender": "Other", 
            "phone": "1234567890"
        }
        res = requests.post(f"{BASE_URL}/api/register", json=reg_payload)
        if res.status_code == 201:
            # Login again to get token
            res = requests.post(f"{BASE_URL}/api/login", json=login_payload)
            return res.json()['token']
    
    log(f"Failed to auth user {email}: {res.text}", "ERROR")
    return None

def run_tests():
    log("Starting API Tests...", "INIT")
    
    # 1. Setup Users
    driver_token = get_auth_token("driver1@test.com", "pass123", "Driver Dave")
    passenger_token = get_auth_token("passenger1@test.com", "pass123", "Passenger Pete")
    
    if not driver_token or not passenger_token:
        return

    driver_headers = {"Authorization": f"Bearer {driver_token}"}
    passenger_headers = {"Authorization": f"Bearer {passenger_token}"}
    
    # 2. Setup: Create a Ride (Driver)
    log("Creating a test ride...", "SETUP")
    ride_payload = {
        "pickup": "University Main Gate",
        "dropoff": "City Center Mall",
        "pickupCoords": {"lat": 24.8607, "lng": 67.0011}, # Karachi coords example
        "dropoffCoords": {"lat": 24.8500, "lng": 67.0100},
        "time": "2024-12-01T10:00:00",
        "seats": 3
    }
    res = requests.post(f"{BASE_URL}/api/ride/create", json=ride_payload, headers=driver_headers)
    if res.status_code != 201:
        log(f"Failed to create ride: {res.text}", "ERROR")
        return
    
    ride_id = res.json()['rideId']
    log(f"Ride Created ID: {ride_id}", "SUCCESS")

    # ==========================================
    # TEST 1: SEARCH RIDES
    # ==========================================
    log("Testing [GET /api/v1/rides/search]...", "TEST")
    # Search for 'University'
    res = requests.get(f"{BASE_URL}/api/v1/rides/search?from=University", headers=passenger_headers)
    if res.status_code == 200 and len(res.json()) > 0:
        log(f"Search successful. Found {len(res.json())} rides.", "SUCCESS")
    else:
        log(f"Search failed: {res.text}", "FAIL")

    # ==========================================
    # TEST 2: JOIN RIDE (Prerequisite for next tests)
    # ==========================================
    log("Passenger joining ride...", "SETUP")
    res = requests.post(f"{BASE_URL}/api/ride/request/{ride_id}", headers=passenger_headers)
    if res.status_code == 200:
        log("Joined ride successfully", "SUCCESS")
    else:
        log(f"Failed to join: {res.text}", "WARN") 
        # Might already be joined if run multiple times, which is fine for next tests

    # ==========================================
    # TEST 3: MY JOINED RIDES
    # ==========================================
    log("Testing [GET /api/v1/my/joined-rides]...", "TEST")
    res = requests.get(f"{BASE_URL}/api/v1/my/joined-rides", headers=passenger_headers)
    rides = res.json()
    # Check if our ride_id is in the returned list
    found = any(r['_id'] == ride_id for r in rides)
    if found:
        log("My Joined Rides verified.", "SUCCESS")
    else:
        log("Ride not found in my joined list", "FAIL")

    # ==========================================
    # TEST 4: CHECK AVAILABILITY
    # ==========================================
    log("Testing [GET /api/v1/ride/{id}/availability]...", "TEST")
    res = requests.get(f"{BASE_URL}/api/v1/ride/{ride_id}/availability", headers=passenger_headers)
    data = res.json()
    # Should have 3 seats total, 1 taken (if new ride)
    log(f"Availability: {data['status']} ({data['remainingSeats']}/{data['totalSeats']} remaining)", "INFO")
    if data['remainingSeats'] < data['totalSeats']:
        log("Availability logic verified.", "SUCCESS")
    else:
        log("Availability logic inconsistent.", "FAIL")

    # ==========================================
    # TEST 5: DRIVER STATS
    # ==========================================
    log("Testing [GET /api/v1/driver/stats]...", "TEST")
    res = requests.get(f"{BASE_URL}/api/v1/driver/stats", headers=driver_headers)
    stats = res.json()
    log(f"Driver Stats: {stats}", "INFO")
    if 'totalRidesOffered' in stats:
        log("Driver stats aggregation successful.", "SUCCESS")
    else:
        log("Driver stats format incorrect.", "FAIL")

    # ==========================================
    # TEST 6: CANCEL RIDE
    # ==========================================
    log("Testing [POST /api/v1/ride/cancel/{id}]...", "TEST")
    res = requests.post(f"{BASE_URL}/api/v1/ride/cancel/{ride_id}", headers=passenger_headers)
    if res.status_code == 200:
        log("Cancellation successful.", "SUCCESS")
        
        # Verify with availability
        res = requests.get(f"{BASE_URL}/api/v1/ride/{ride_id}/availability", headers=passenger_headers)
        data = res.json()
        if data['remainingSeats'] == data['totalSeats']:
             log("Verification: Passenger list empty after cancel.", "SUCCESS")
    else:
        log(f"Cancellation failed: {res.text}", "FAIL")

if __name__ == "__main__":
    run_tests()
