document.addEventListener('DOMContentLoaded', function() {
    const data = window.healthData;
    const limits = window.thresholds;

    // 1. Safety Check: If no data, stop here
    if (!data || !data.labels || data.labels.length === 0) {
        console.warn("No data found to display charts.");
        return;
    }

    // 2. Chart Creation Logic
    function createChart(canvasId, label, dataPoints, color, thresholdValue) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const safeData = dataPoints || [];
        
        try {
            new Chart(canvas.getContext('2d'), {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: label,
                        data: safeData,
                        borderColor: color,
                        backgroundColor: color + '15',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4
                    },
                    {
                        label: 'Limit',
                        // Draws the dashed red line based on Admin Max values
                        data: Array(data.labels.length).fill(thresholdValue || 0),
                        borderColor: '#ff0000',
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { 
                        legend: { display: false },
                        tooltip: { mode: 'index', intersect: false }
                    },
                    scales: {
                        y: { beginAtZero: false }
                    }
                }
            });
        } catch (err) {
            console.error(`Error initializing ${label} chart:`, err);
        }
    }

    // 3. Initialize Charts with Admin Thresholds
    createChart('hrChart', 'Heart Rate', data.heart_rate, '#ef4444', limits.hr_max);
    createChart('bpSysChart', 'Systolic BP', data.systolic, '#3b82f6', limits.sys_max);
    createChart('bpDiaChart', 'Diastolic BP', data.diastolic, '#10b981', limits.dia_max);
    createChart('glucoseChart', 'Glucose', data.glucose, '#f59e0b', limits.glucose_max);

    // 4. Alert Logic (Updated to use correct 'max' property names)
    function checkVitalsAlerts() {
        const alertContainer = document.getElementById('alert-container');
        if (!alertContainer) return;

        let alerts = [];

        // Check the most recent reading (index 0 if sorted [::-1] in Python)
        if (data.heart_rate && data.heart_rate[0] > limits.hr_max) {
            alerts.push(`High Heart Rate: ${data.heart_rate[0]} BPM`);
        }
        if (data.systolic && data.systolic[0] > limits.sys_max) {
            alerts.push(`High Systolic BP: ${data.systolic[0]} mmHg`);
        }
        if (data.glucose && data.glucose[0] > limits.glucose_max) {
            alerts.push(`High Glucose: ${data.glucose[0]} mg/dL`);
        }

        // Render the Alert Banner
        if (alerts.length > 0) {
            alertContainer.innerHTML = `
                <div class="bg-red-50 border-l-4 border-red-600 p-4 rounded-r-lg shadow-md animate-pulse">
                    <div class="flex items-center">
                        <i class="fas fa-exclamation-triangle text-red-600 text-xl mr-3"></i>
                        <div>
                            <p class="text-red-800 font-bold">Health Alert Triggered</p>
                            <p class="text-red-700 text-sm font-medium">${alerts.join(' | ')}</p>
                        </div>
                    </div>
                </div>
            `;
        }
    }

    checkVitalsAlerts();
});