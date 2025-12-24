let chartInstance = null;

// Helper function to create a striped pattern
function createStripedPattern(ctx, baseColor) {
    const canvas = document.createElement('canvas');
    canvas.width = 10;
    canvas.height = 10;
    const patternCtx = canvas.getContext('2d');

    // Fill with base color
    patternCtx.fillStyle = baseColor;
    patternCtx.fillRect(0, 0, 10, 10);

    // Add white diagonal stripes
    patternCtx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    patternCtx.lineWidth = 2;
    patternCtx.beginPath();
    patternCtx.moveTo(0, 10);
    patternCtx.lineTo(10, 0);
    patternCtx.stroke();

    return ctx.createPattern(canvas, 'repeat');
}

document.getElementById('head-to-head-form').addEventListener('submit', function(event) {
    event.preventDefault();
    const driver1 = document.getElementById('driver1').value.trim().toUpperCase();
    const driver2 = document.getElementById('driver2').value.trim().toUpperCase();
    const resultDiv = document.getElementById('head-to-head-result');
    const loadingDiv = document.getElementById('loading-indicator');

    if (driver1 && driver2) {
        // Show loading indicator
        loadingDiv.style.display = 'block';
        resultDiv.innerHTML = '';

        // Destroy existing chart if any
        if (chartInstance) {
            chartInstance.destroy();
            chartInstance = null;
        }

        fetch(`/api/head_to_head/${driver1}/${driver2}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.error || 'Server error'); });
                }
                return response.json();
            })
            .then(data => {
                // Hide loading indicator
                loadingDiv.style.display = 'none';

                const d1Code = Object.keys(data)[0];
                const d2Code = Object.keys(data)[1];
                const d1Data = DRIVERS[d1Code] || {};
                const d2Data = DRIVERS[d2Code] || {};
                const d1Wins = data[d1Code];
                const d2Wins = data[d2Code];

                // Check if they are teammates
                const areTeammates = d1Data.team && d2Data.team && d1Data.team === d2Data.team;

                // Create chart container
                const chartContainer = document.createElement('div');
                chartContainer.className = 'chart-container';
                chartContainer.innerHTML = '<canvas id="head-to-head-chart"></canvas>';
                resultDiv.appendChild(chartContainer);

                // Get canvas context
                const ctx = document.getElementById('head-to-head-chart').getContext('2d');

                // Prepare colors
                let d1Color = d1Data.color || '#666';
                let d2Color = d2Data.color || '#666';
                let d1Pattern = d1Color;
                let d2Pattern = d2Color;

                // If teammates, make second driver striped
                if (areTeammates) {
                    d2Pattern = createStripedPattern(ctx, d2Color);
                }

                // Create pie chart
                chartInstance = new Chart(ctx, {
                    type: 'pie',
                    data: {
                        labels: [
                            `${d1Data.name || d1Code}`,
                            `${d2Data.name || d2Code}`
                        ],
                        datasets: [{
                            data: [d1Wins, d2Wins],
                            backgroundColor: [d1Pattern, d2Pattern],
                            borderColor: ['#fff', '#fff'],
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                display: false
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.label || '';
                                        const value = context.parsed || 0;
                                        const total = d1Wins + d2Wins;
                                        const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                        return `${label}: ${value} wins (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });

                // Create custom legend
                const legendDiv = document.createElement('div');
                legendDiv.className = 'chart-legend';

                const legend1 = document.createElement('div');
                legend1.className = 'legend-item';
                const colorBox1 = document.createElement('div');
                colorBox1.className = 'legend-color-box';
                colorBox1.style.backgroundColor = d1Color;
                const total = d1Wins + d2Wins;
                const d1Percentage = total > 0 ? ((d1Wins / total) * 100).toFixed(1) : 0;
                legend1.innerHTML = `
                    ${colorBox1.outerHTML}
                    <span><strong>${d1Data.name || d1Code}</strong>: ${d1Wins} wins (${d1Percentage}%)</span>
                `;

                const legend2 = document.createElement('div');
                legend2.className = 'legend-item';
                const colorBox2 = document.createElement('div');
                colorBox2.className = `legend-color-box${areTeammates ? ' legend-striped' : ''}`;
                colorBox2.style.backgroundColor = d2Color;
                const d2Percentage = total > 0 ? ((d2Wins / total) * 100).toFixed(1) : 0;
                legend2.innerHTML = `
                    ${colorBox2.outerHTML}
                    <span><strong>${d2Data.name || d2Code}</strong>: ${d2Wins} wins (${d2Percentage}%)${areTeammates ? ' (Teammate)' : ''}</span>
                `;

                legendDiv.appendChild(legend1);
                legendDiv.appendChild(legend2);
                resultDiv.appendChild(legendDiv);
            })
            .catch(error => {
                // Hide loading indicator
                loadingDiv.style.display = 'none';
                console.error('Error fetching head-to-head data:', error);
                resultDiv.innerHTML = `<p class="driver-result" style="color: var(--f1-red);">Error: ${error.message}</p>`;
            });
    }
});
