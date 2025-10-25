document.addEventListener('DOMContentLoaded', () => {
    const sosBtn = document.getElementById('sosBtn');
    const status = document.getElementById('status');

    // Initialize map
    const map = L.map('map').setView([0, 0], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data © <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'
    }).addTo(map);
    let marker = null;
    let accuracyCircle = null;

    // Function to update user location on the map
    function updateMap(lat, lon, accuracy) {
        if (marker) {
            marker.setLatLng([lat, lon]);
        } else {
            marker = L.marker([lat, lon]).addTo(map);
        }

        // Show accuracy circle
        if (accuracyCircle) {
            accuracyCircle.setLatLng([lat, lon]);
            accuracyCircle.setRadius(accuracy);
        } else {
            accuracyCircle = L.circle([lat, lon], { radius: accuracy, color: 'blue', fillColor: '#blue', fillOpacity: 0.2 }).addTo(map);
        }

        map.setView([lat, lon], 15);
        status.innerHTML = `Current Location: ${lat.toFixed(5)}, ${lon.toFixed(5)}<br>Accuracy: ±${accuracy.toFixed(1)} meters`;
    }

    // Continuously watch user location until good accuracy is achieved
    if (navigator.geolocation) {
        const watchId = navigator.geolocation.watchPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                const accuracy = position.coords.accuracy; // in meters

                updateMap(lat, lon, accuracy);

                // Only stop watching if accuracy is good (less than 30 meters)
                if (accuracy <= 30) {
                    navigator.geolocation.clearWatch(watchId);
                    status.innerHTML += "<br>Location acquired accurately!";
                }
            },
            (err) => {
                console.error(err);
                switch(err.code) {
                    case err.PERMISSION_DENIED:
                        status.innerHTML = "Permission denied. Please allow location access.";
                        break;
                    case err.POSITION_UNAVAILABLE:
                        status.innerHTML = "Location information is unavailable.";
                        break;
                    case err.TIMEOUT:
                        status.innerHTML = "Getting location timed out. Please try again.";
                        break;
                    default:
                        status.innerHTML = "An unknown error occurred while fetching location.";
                }
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    } else {
        status.innerHTML = "Geolocation is not supported by your browser.";
    }

    // SOS Button click
    sosBtn.addEventListener('click', () => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition((position) => {
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;

                fetch('/sos', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ latitude, longitude })
                })
                .then(res => res.json())
                .then(data => {
                    status.innerHTML = `<b>${data.message}</b><br>
                    <strong>Contacts notified:</strong> ${data.contacts_notified.join(', ')}<br>
                    <strong>Nearby volunteers:</strong> ${data.volunteers_notified.join(', ')}<br>
                    <strong>Area safe:</strong> ${data.area_safe}`;
                })
                .catch(err => {
                    status.innerHTML = "Error sending SOS. Please try again.";
                    console.error(err);
                });
            }, (err) => {
                status.innerHTML = "Unable to retrieve your location for SOS.";
                console.error(err);
            }, { enableHighAccuracy: true, timeout: 10000 });
        } else {
            status.innerHTML = "Geolocation is not supported by your browser.";
        }
    });
});
