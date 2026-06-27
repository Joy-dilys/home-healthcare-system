/**
 * main.js
 * * This file is for advanced or complex client-side JavaScript features 
 * such as real-time updates and data visualization.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if the current page is the dashboard
    if (document.getElementById('alert-list')) {
        console.log("Dashboard loaded. Initiating client-side monitoring features...");
        
        // **Future Feature: Implement Charting**
        // This function would fetch detailed historical data for a selected patient 
        // and render a line graph using a library like Chart.js.
        // Example: loadPatientChart(patientId);

        // **Future Feature: Real-Time Polling**
        // For a true real-time view without WebSockets, you'd periodically check for new alerts.
        // setInterval(fetchNewAlerts, 10000); // Poll every 10 seconds

        // The simple resolveAlert function can be defined here too
    }

    // Example of a function that could be called from the dashboard
    function loadPatientChart(patientId) {
        console.log(`Loading chart data for patient ${patientId}...`);
        // Example Fetch:
        // fetch(`/api/data/${patientId}`)
        //   .then(response => response.json())
        //   .then(data => {
        //       // Use Chart.js to render the data (HR, BP, Glucose)
        //   });
    }

    // You can attach event listeners here instead of inline 'onclick' in HTML
    // const resolveButtons = document.querySelectorAll('.alert-button');
    // resolveButtons.forEach(button => {
    //     button.addEventListener('click', function() {
    //         const alertId = this.getAttribute('data-alert-id'); // assuming you add this attribute
    //         resolveAlert(alertId);
    //     });
    // });
});


// Note: Ensure the core resolveAlert() function (from dashboard.html) 
// is either moved here OR remains in the HTML file for now, 
// and the script is correctly linked in your HTML <head> section:
// <script src="{{ url_for('static', filename='js/main.js') }}"></script>