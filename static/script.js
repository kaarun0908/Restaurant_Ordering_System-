
document.addEventListener("DOMContentLoaded", function () {
    // Location popup
    const locationButton = document.getElementById("locationButton");
    const locationPopup = document.getElementById("locationPopup");
    const closeLocation = document.getElementById("closeLocation");
    const locationInput = document.getElementById("locationInput");
    const saveLocation = document.getElementById("saveLocation");
    const locationText = document.getElementById("locationText");

    // Restore the saved delivery location
    if (locationText) {
        const savedLocation = localStorage.getItem("foodiesLocation");

        if (savedLocation) {
            locationText.textContent = savedLocation;
        }
    }

    // Open location popup
    if (locationButton && locationPopup) {
        locationButton.addEventListener("click", function () {
            locationPopup.hidden = !locationPopup.hidden;
        });
    }

    // Close location popup
    if (closeLocation && locationPopup) {
        closeLocation.addEventListener("click", function () {
            locationPopup.hidden = true;
        });
    }

    // Save delivery location
    if (saveLocation && locationPopup && locationInput && locationText) {
        saveLocation.addEventListener("click", function () {
            const location = locationInput.value.trim();

            if (!location) {
                alert("Please enter your delivery location.");
                return;
            }

            localStorage.setItem("foodiesLocation", location);
            locationText.textContent = location;
            locationPopup.hidden = true;

            alert("Delivery location saved!");
        });
    }

    // Close popup when clicking outside it
    document.addEventListener("click", function (event) {
        if (
            locationPopup &&
            locationButton &&
            !locationPopup.hidden &&
            !locationPopup.contains(event.target) &&
            !locationButton.contains(event.target)
        ) {
            locationPopup.hidden = true;
        }
    });

    // Confirm before submitting an order
    const checkoutForm = document.querySelector(
        'form[action*="checkout"]'
    );

    if (checkoutForm) {
        checkoutForm.addEventListener("submit", function (event) {
            const confirmed = confirm(
                "Are you sure you want to place this order?"
            );

            if (!confirmed) {
                event.preventDefault();
            }
        });
    }

    // Prevent accidental empty search submissions
    document.querySelectorAll(".nav-search, .menu-search").forEach(
        function (searchForm) {
            searchForm.addEventListener("submit", function (event) {
                const searchInput = searchForm.querySelector(
                    'input[name="q"]'
                );

                if (searchInput && !searchInput.value.trim()) {
                    event.preventDefault();
                    searchInput.focus();
                }
            });
        }
    );
});
