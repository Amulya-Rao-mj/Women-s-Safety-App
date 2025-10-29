document.addEventListener('DOMContentLoaded', () => {
    const sosBtn = document.getElementById('sosBtn');
    const status = document.getElementById('status');

    const map = L.map('map').setView([0, 0], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data © OpenStreetMap contributors'
    }).addTo(map);

    let marker = null;
    let accuracyCircle = null;

    function updateMap(lat, lon, accuracy) {
        if (marker) {
            marker.setLatLng([lat, lon]);
        } else {
            marker = L.marker([lat, lon]).addTo(map);
        }

        if (accuracyCircle) {
            accuracyCircle.setLatLng([lat, lon]);
            accuracyCircle.setRadius(accuracy);
        } else {
            accuracyCircle = L.circle([lat, lon], { radius: accuracy }).addTo(map);
        }

        map.setView([lat, lon], 16);
        status.innerHTML = `Latitude: ${lat.toFixed(5)}, Longitude: ${lon.toFixed(5)}<br>
        Accuracy: ±${accuracy.toFixed(1)}m`;
    }

    if (navigator.geolocation) {
        navigator.geolocation.watchPosition(
            position => {
                updateMap(position.coords.latitude, position.coords.longitude, position.coords.accuracy);
            },
            error => {
                status.innerHTML = "Location access error: " + error.message;
            },
            { enableHighAccuracy: true }
        );
    } else {
        status.innerHTML = "Geolocation not supported.";
    }

    sosBtn.addEventListener('click', () => {
        navigator.geolocation.getCurrentPosition(position => {
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
                    Contacts: ${data.contacts_notified}<br>
                    Volunteers: ${data.volunteers_notified}<br>
                    Safe: ${data.area_safe}`;
                })
                .catch(() => {
                    status.innerHTML = "Error sending SOS.";
                });
        });
    });
});
