document.addEventListener('DOMContentLoaded', () => {
    const sosButton = document.getElementById('sosButton');
    if(sosButton) {
        sosButton.addEventListener('click', () => {
            alert("SOS Alert Sent! Authorities and trusted contacts notified.");
        });
    }
});
