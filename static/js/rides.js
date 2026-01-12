const token = localStorage.getItem('token');
const userStr = localStorage.getItem('user');

if (!token || !userStr) {
    if (!window.location.href.includes('auth')) window.location.href = '/auth';
} else {
    const user = JSON.parse(userStr);
    const nameEl = document.getElementById('userName');
    const emailEl = document.getElementById('userEmail');
    const avatarEl = document.getElementById('profileAvatar');

    if (nameEl) nameEl.innerText = user.name;
    if (emailEl) emailEl.innerText = user.email;
    if (avatarEl && user.name) {
        avatarEl.innerText = user.name.charAt(0).toUpperCase();
    }
}

// Utility to create Request with Auth Header
const authFetch = (url, options = {}) => {
    const headers = options.headers || {};
    headers['Authorization'] = `Bearer ${token}`;
    headers['Content-Type'] = 'application/json';
    return fetch(url, { ...options, headers });
};

// Create Ride Logic
const createForm = document.getElementById('createRideForm');
let selectionMap = null;
let pickupPoint = null; // {lat, lng}
let dropoffPoint = null;
let pickupMarker = null;
let dropoffMarker = null;
let routeLine = null;

// ---------------------------------------------
// FORWARD GEOCODING (Search & Pin)
// ---------------------------------------------
async function searchLocation(type) {
    const inputId = type === 'pickup' ? 'cPickup' : 'cDropoff';
    const query = document.getElementById(inputId).value;

    if (!query) {
        alert("Please type a location name first!");
        return;
    }

    try {
        const statusEl = document.getElementById('selectionStatus');
        statusEl.innerText = `Searching for "${query}"...`;

        // Nominatim OpenStreetMap Search API
        const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`);
        const results = await res.json();

        if (results.length > 0) {
            const topResult = results[0];
            const lat = parseFloat(topResult.lat);
            const lng = parseFloat(topResult.lon);

            // Center Map
            if (selectionMap) selectionMap.setView([lat, lng], 16);

            // Set Pin (Reuse existing logic)
            if (type === 'pickup') {
                setPickup(lat, lng, true); // true = auto/search, suppresses reverse geo overwrite if we want (logic in setPickup might need check)
                // Actually setPickup calls reverseGeocode. 
                // To avoid overwriting what user typed with "Address...", we can modify setPickup or just let it be detailed.
                // Let's rely on setPickup for consistency, but maybe update input value back to nice name if needed? 
                // Actually Nominatim reverse often gives better structured data than raw user input, so it's fine.
            } else {
                setDropoff(lat, lng);
            }

            statusEl.innerText = `Found: ${topResult.display_name.split(',')[0]}`;
        } else {
            alert("Location not found. Try a different name.");
            statusEl.innerText = "Location not found.";
        }
    } catch (err) {
        console.error("Search failed", err);
        alert("Error searching location");
    }
}

// Reverse Geocoding Helper (Nominatim)
async function reverseGeocode(lat, lng, elementId) {
    // If this change came from a search, we might not want to overwrite the input immediately with "Fetching..."
    // But for consistency:
    const el = document.getElementById(elementId);

    if (el) {
        el.value = "Fetching address...";
        el.disabled = true;
    }

    try {
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`);
        const data = await res.json();
        if (el) {
            el.value = data.display_name || "Unknown Location";
            el.disabled = false;
        }
    } catch (err) {
        console.error("Geocoding failed", err);
        if (el) {
            el.value = "Location selected (Address lookup failed)";
            el.disabled = false;
        }
    }
}

// Initialize Selection Map called by showSection('create')
window.initSelectionMap = function () {
    if (selectionMap) {
        selectionMap.invalidateSize();
        return;
    }

    // Default view
    const defaultLat = 40.75;
    const defaultLng = -73.98;

    selectionMap = L.map('selectionMap').setView([defaultLat, defaultLng], 13);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap'
    }).addTo(selectionMap);

    // Map Click Handler for Selection (Logic updated for Auto-Pickup)
    selectionMap.on('click', function (e) {
        const { lat, lng } = e.latlng;

        // If Pickup is somehow not set (geo failed), set it first
        if (!pickupPoint) {
            setPickup(lat, lng);
        } else if (!dropoffPoint) {
            setDropoff(lat, lng);
        } else {
            alert("Both points set. Click Reset to change.");
        }
    });

    // Auto-Geolocate for Pickup
    if (navigator.geolocation) {
        document.getElementById('selectionStatus').innerText = "Locating you for Pickup...";
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const { latitude, longitude } = pos.coords;
                selectionMap.setView([latitude, longitude], 15);
                setPickup(latitude, longitude, true); // true = auto detected
            },
            (err) => {
                console.warn("Geolocation failed", err);
                document.getElementById('selectionStatus').innerText = "Location access denied. Please click map to set Pickup.";
            }
        );
    }
};

function setPickup(lat, lng, isAuto = false) {
    pickupPoint = { lat, lng };

    // Add Green Marker
    pickupMarker = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'custom-icon',
            html: '<div style="background-color:green; width:14px; height:14px; border-radius:50%; border:2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>'
        })
    }).addTo(selectionMap).bindPopup(isAuto ? "Your Location (Pickup)" : "Pickup Point").openPopup();

    // Fill Address
    reverseGeocode(lat, lng, 'cPickup');

    document.getElementById('selectionStatus').innerText = "Pickup set! Click map for Dropoff.";
    document.getElementById('selectionStatus').style.color = "orange";
}

function setDropoff(lat, lng) {
    dropoffPoint = { lat, lng };

    // Add Red Marker
    dropoffMarker = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'custom-icon',
            html: '<div style="background-color:red; width:14px; height:14px; border-radius:50%; border:2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>'
        })
    }).addTo(selectionMap).bindPopup("Dropoff Point").openPopup();

    // Fill Address
    reverseGeocode(lat, lng, 'cDropoff');

    // Draw line
    if (pickupPoint) {
        routeLine = L.polyline([
            [pickupPoint.lat, pickupPoint.lng],
            [dropoffPoint.lat, dropoffPoint.lng]
        ], { color: 'blue', dashArray: '5, 10' }).addTo(selectionMap);
    }

    document.getElementById('selectionStatus').innerText = "Ready to Post Ride.";
    document.getElementById('selectionStatus').style.color = "green";
}

window.resetSelectionMap = function () {
    if (!selectionMap) return;
    pickupPoint = null;
    dropoffPoint = null;
    if (pickupMarker) selectionMap.removeLayer(pickupMarker);
    if (dropoffMarker) selectionMap.removeLayer(dropoffMarker);
    if (routeLine) selectionMap.removeLayer(routeLine);

    document.getElementById('cPickup').value = "";
    document.getElementById('cDropoff').value = "";
    document.getElementById('selectionStatus').innerText = "Points reset.";

    // If we want to re-trigger auto-locate, we could call initSelectionMap again?
    // Or just let user click manually. Let's let user click manually to avoid annoying prompts or logic loops.
    document.getElementById('selectionStatus').innerText = "Click map to set Pickup.";
}

if (createForm) {
    createForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!pickupPoint || !dropoffPoint) {
            alert("Please select Pickup and Dropoff points!");
            return;
        }

        const payload = {
            pickup: document.getElementById('cPickup').value,
            dropoff: document.getElementById('cDropoff').value,
            // Backend expects { lng, lat }
            pickupCoords: { lng: pickupPoint.lng, lat: pickupPoint.lat },
            dropoffCoords: { lng: dropoffPoint.lng, lat: dropoffPoint.lat },
            time: document.getElementById('cTime').value,
            seats: document.getElementById('cSeats').value
        };

        try {
            const res = await authFetch('/api/v1/ride/create', {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                alert('Ride Created Successfully!');
                loadMyRides();
                createForm.reset();
                resetSelectionMap();
                showSection('myrides'); // Switch tab
            } else {
                alert(data.message);
            }
        } catch (err) { console.error(err); }
    });
}

// ---------------- SEARCH RIDES ----------------
async function searchRides() {
    const pickup = document.getElementById('searchFrom').value;
    const dropoff = document.getElementById('searchTo').value;

    const query = new URLSearchParams({ from: pickup, to: dropoff });
    const res = await authFetch(`/api/v1/rides/search?${query}`);
    const rides = await res.json();
    renderRides(rides);
}

let map = null;
let currentMarkers = [];

// ---------------- GEO SEARCH ----------------
async function findNearbyRides() {
    if (!navigator.geolocation) {
        alert("Geolocation not supported");
        return;
    }

    navigator.geolocation.getCurrentPosition(async ({ coords }) => {
        const lat = coords.latitude;
        const lng = coords.longitude;

        document.getElementById('map-container').style.display = 'block';

        if (!map) {
            map = L.map('map').setView([lat, lng], 13);
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        } else {
            map.setView([lat, lng], 13);
            map.invalidateSize();
        }

        currentMarkers.forEach(m => map.removeLayer(m));
        currentMarkers = [];

        currentMarkers.push(
            L.marker([lat, lng]).addTo(map).bindPopup("📍 You are here").openPopup()
        );

        try {
            const res = await authFetch(`/api/v1/rides/nearby?lat=${lat}&lng=${lng}`);
            const rides = await res.json();
            renderRides(rides);

            rides.forEach(ride => {
                if (!ride.pickupCoords?.coordinates) return;

                const [rLng, rLat] = ride.pickupCoords.coordinates;
                const seatsLeft = ride.seats - (ride.passengers?.length || 0);

                const popup = `
                    <b>${ride.pickup} ➝ ${ride.dropoff}</b><br>
                    Seats Left: ${seatsLeft}<br>
                    <button ${seatsLeft <= 0 ? 'disabled' : ''}
                        onclick="joinRide('${ride._id}')">
                        ${seatsLeft <= 0 ? 'Full' : 'Request Ride'}
                    </button>
                `;

                currentMarkers.push(
                    L.marker([rLat, rLng]).addTo(map).bindPopup(popup)
                );
            });

        } catch (err) {
            alert("Error fetching nearby rides");
            console.error(err);
        }
    });
}

// ---------------- RENDER RIDES ----------------
function renderRides(rides) {
    const container = document.getElementById('rideResults');
    container.innerHTML = '';

    if (!rides.length) {
        container.innerHTML = '<p>No rides found.</p>';
        return;
    }

    rides.forEach(ride => {
        const seatsLeft = ride.seats - (ride.passengers?.length || 0);

        // Smart Match Score Badge (if present)
        let scoreBadge = '';
        if (ride.matchScore !== undefined) {
            let color = 'green';
            if (ride.matchScore < 50) color = 'red';
            else if (ride.matchScore < 80) color = 'orange';

            scoreBadge = `<div style="position:absolute; top:10px; right:10px; background:${color}; color:white; padding:4px 8px; border-radius:12px; font-weight:bold; font-size:0.8em;">
                Match: ${ride.matchScore}%
             </div>`;
        }

        const div = document.createElement('div');
        div.className = 'ride-card';
        div.style.position = 'relative'; // For badge positioning

        div.innerHTML = `
            ${scoreBadge}
            <h4>${ride.pickup} ➝ ${ride.dropoff}</h4>
            <p>📅 ${new Date(ride.time).toLocaleString()}</p>
            <p>💺 Seats Left: ${seatsLeft}</p>
            <div class="card-actions">
                <button class="join-btn"
                    ${seatsLeft <= 0 ? 'disabled' : ''}
                    onclick="joinRide('${ride._id}')">
                    ${seatsLeft <= 0 ? 'Full' : 'Request Ride'}
                </button>
                <button class="secondary-btn"
                    onclick="checkAvailability('${ride._id}')">
                    Check Availability
                </button>
            </div>
        `;
        container.appendChild(div);
    });
}

// ---------------- JOIN / CANCEL ----------------
async function joinRide(rideId) {
    const res = await authFetch(`/api/v1/ride/request/${rideId}`, { method: 'POST' });
    const data = await res.json();
    alert(data.message);
    searchRides();
}

async function cancelRide(rideId) {
    if (!confirm("Cancel this ride request?")) return;
    const res = await authFetch(`/api/v1/ride/cancel/${rideId}`, { method: 'POST' });
    const data = await res.json();
    alert(data.message);
    loadMyRides();
}

// ---------------- AVAILABILITY ----------------
async function checkAvailability(rideId) {
    const res = await authFetch(`/api/v1/ride/${rideId}/availability`);
    const data = await res.json();
    alert(`Status: ${data.status}\nRemaining: ${data.remainingSeats}/${data.totalSeats}`);
}

// ---------------- MY RIDES ----------------
async function loadMyRides() {
    const container = document.getElementById('myRidesList');
    if (!container) return;

    const driven = await authFetch('/api/v1/my/rides').then(r => r.json());
    const joined = await authFetch('/api/v1/my/joined-rides').then(r => r.json());

    let html = '<h3>Offered Rides</h3>';
    driven.driven_rides.forEach(r =>
        html += `<div class="ride-card">${r.pickup} ➝ ${r.dropoff}</div>`
    );

    html += '<h3>Joined Rides</h3>';
    joined.forEach(r =>
        html += `<div class="ride-card">${r.pickup} ➝ ${r.dropoff}
        <button onclick="cancelRide('${r._id}')">Leave</button></div>`
    );

    container.innerHTML = html;
}

// ---------------- STATS ----------------
async function loadStats() {
    // 1. Driver Stats
    const resStats = await authFetch('/api/v1/driver/stats');
    const stats = await resStats.json();

    // 2. Popular Routes Analytics
    const resRoutes = await authFetch('/api/v1/analytics/popular-routes');
    const routes = await resRoutes.json();

    let routesHtml = '<ul style="list-style:none; padding:0; margin-top:10px;">';
    routes.forEach((r, index) => {
        routesHtml += `
            <li style="background:#f8f9fa; margin-bottom:8px; padding:10px; border-radius:8px; display:flex; justify-content:space-between;">
                <span><b>#${index + 1}</b> ${r._id.from} ➝ ${r._id.to}</span>
                <span style="color:var(--primary); font-weight:bold;">${r.rideCount} rides</span>
            </li>
        `;
    });
    routesHtml += '</ul>';

    document.getElementById('statsList').innerHTML = `
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
            <div class="stat-card" style="background:white; padding:20px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.05);">
                <h3 style="margin-bottom:15px; color:var(--dark);">👤 Your Performance</h3>
                <div style="display:flex; flex-direction:column; gap:10px;">
                     <div style="display:flex; justify-content:space-between; padding-bottom:5px; border-bottom:1px solid #eee;">
                        <span>Total Rides Offered:</span> <b>${stats.totalRidesOffered}</b>
                     </div>
                     <div style="display:flex; justify-content:space-between; padding-bottom:5px; border-bottom:1px solid #eee;">
                        <span>Total Passengers:</span> <b>${stats.totalPassengersCarried}</b>
                     </div>
                     <div style="display:flex; justify-content:space-between;">
                        <span>Avg Passengers:</span> <b>${stats.averagePassengersPerRide.toFixed(1)}</b>
                     </div>
                </div>
            </div>

            <div class="stat-card" style="background:white; padding:20px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.05);">
                <h3 style="margin-bottom:15px; color:var(--dark);">🔥 Hot Routes</h3>
                ${routes.length ? routesHtml : '<p>No data yet.</p>'}
            </div>
        </div>
    `;
}
