let chartInstance = null;
let selectedDriver1 = null;
let selectedDriver2 = null;

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

// --- Slot rendering ---

function renderSlot(slotNum, driverCode) {
    const slot = document.getElementById(`h2h-slot-${slotNum}`);
    if (!driverCode) {
        slot.classList.remove('filled');
        slot.innerHTML = `
            <div class="h2h-slot-empty">
                <span class="h2h-slot-label">Driver ${slotNum}</span>
                <span class="h2h-slot-hint">Select below</span>
            </div>`;
        return;
    }
    const d = DRIVERS[driverCode] || {};
    slot.classList.add('filled');
    slot.style.setProperty('--team-color', d.color || '#666');
    slot.innerHTML = `
        <div class="h2h-slot-filled">
            <span class="h2h-slot-number" style="background: ${d.color || '#666'};">${d.number || ''}</span>
            <div class="h2h-slot-info">
                <span class="h2h-slot-name">${d.flag || ''} ${d.name || driverCode}</span>
                <span class="h2h-slot-team">${d.team || ''}</span>
            </div>
            <span class="h2h-slot-clear" title="Remove driver">&times;</span>
        </div>`;
}

function updateUI() {
    // Update slots
    renderSlot(1, selectedDriver1);
    renderSlot(2, selectedDriver2);

    // Update grid card states
    document.querySelectorAll('.h2h-driver-card').forEach(card => {
        const code = card.dataset.code;
        card.classList.toggle('selected', code === selectedDriver1 || code === selectedDriver2);
    });

    // Update swap button
    document.getElementById('h2h-swap-btn').disabled = !(selectedDriver1 && selectedDriver2);

    // Update prompt text
    const prompt = document.getElementById('h2h-prompt');
    if (!selectedDriver1 && !selectedDriver2) {
        prompt.textContent = 'Click two drivers below to compare';
    } else if (!selectedDriver1 || !selectedDriver2) {
        prompt.textContent = 'Select one more driver to compare';
    } else {
        prompt.textContent = '';
    }
}

// --- Comparison fetch ---

function runComparison() {
    if (!selectedDriver1 || !selectedDriver2) return;

    const resultDiv = document.getElementById('head-to-head-result');
    const loadingDiv = document.getElementById('loading-indicator');

    loadingDiv.style.display = 'block';
    resultDiv.innerHTML = '';

    if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null;
    }

    fetch(`/api/head_to_head/${selectedDriver1}/${selectedDriver2}?season=${CURRENT_SEASON}`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || 'Server error'); });
            }
            return response.json();
        })
        .then(data => {
            loadingDiv.style.display = 'none';

            const d1Code = Object.keys(data)[0];
            const d2Code = Object.keys(data)[1];
            const d1Data = DRIVERS[d1Code] || {};
            const d2Data = DRIVERS[d2Code] || {};
            const d1Wins = data[d1Code];
            const d2Wins = data[d2Code];

            const areTeammates = d1Data.team && d2Data.team && d1Data.team === d2Data.team;

            // Create chart container
            const chartContainer = document.createElement('div');
            chartContainer.className = 'chart-container';
            chartContainer.innerHTML = '<canvas id="head-to-head-chart"></canvas>';
            resultDiv.appendChild(chartContainer);

            const ctx = document.getElementById('head-to-head-chart').getContext('2d');

            let d1Color = d1Data.color || '#666';
            let d2Color = d2Data.color || '#666';
            let d1Pattern = d1Color;
            let d2Pattern = d2Color;

            if (areTeammates) {
                d2Pattern = createStripedPattern(ctx, d2Color);
            }

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
                        legend: { display: false },
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

            // Custom legend
            const legendDiv = document.createElement('div');
            legendDiv.className = 'chart-legend';

            const total = d1Wins + d2Wins;
            const d1Percentage = total > 0 ? ((d1Wins / total) * 100).toFixed(1) : 0;
            const d2Percentage = total > 0 ? ((d2Wins / total) * 100).toFixed(1) : 0;

            const legend1 = document.createElement('div');
            legend1.className = 'legend-item';
            const colorBox1 = document.createElement('div');
            colorBox1.className = 'legend-color-box';
            colorBox1.style.backgroundColor = d1Color;
            legend1.innerHTML = `
                ${colorBox1.outerHTML}
                <span><a href="/driver/${d1Code}?season=${CURRENT_SEASON}"><strong>${d1Data.name || d1Code}</strong></a>: ${d1Wins} wins (${d1Percentage}%)</span>
            `;

            const legend2 = document.createElement('div');
            legend2.className = 'legend-item';
            const colorBox2 = document.createElement('div');
            colorBox2.className = `legend-color-box${areTeammates ? ' legend-striped' : ''}`;
            colorBox2.style.backgroundColor = d2Color;
            legend2.innerHTML = `
                ${colorBox2.outerHTML}
                <span><a href="/driver/${d2Code}?season=${CURRENT_SEASON}"><strong>${d2Data.name || d2Code}</strong></a>: ${d2Wins} wins (${d2Percentage}%)${areTeammates ? ' (Teammate)' : ''}</span>
            `;

            legendDiv.appendChild(legend1);
            legendDiv.appendChild(legend2);
            resultDiv.appendChild(legendDiv);
        })
        .catch(error => {
            loadingDiv.style.display = 'none';
            console.error('Error fetching head-to-head data:', error);
            resultDiv.innerHTML = `<p class="driver-result" style="color: var(--f1-red);">Error: ${error.message}</p>`;
        });
}

// --- Event handlers ---

// Driver card click
document.getElementById('h2h-driver-grid').addEventListener('click', function(e) {
    const card = e.target.closest('.h2h-driver-card');
    if (!card) return;

    const code = card.dataset.code;

    // If already selected, deselect
    if (code === selectedDriver1) {
        selectedDriver1 = null;
        updateUI();
        return;
    }
    if (code === selectedDriver2) {
        selectedDriver2 = null;
        updateUI();
        return;
    }

    // Fill next empty slot
    if (!selectedDriver1) {
        selectedDriver1 = code;
    } else if (!selectedDriver2) {
        selectedDriver2 = code;
    } else {
        // Both full — replace slot 2
        selectedDriver2 = code;
    }

    updateUI();

    if (selectedDriver1 && selectedDriver2) {
        runComparison();
    }
});

// Slot click — clear the slot
document.querySelectorAll('.h2h-slot').forEach(slot => {
    slot.addEventListener('click', function(e) {
        // Only clear if the slot is filled
        if (!this.classList.contains('filled')) return;
        const slotNum = this.dataset.slot;
        if (slotNum === '1') {
            selectedDriver1 = null;
        } else {
            selectedDriver2 = null;
        }
        updateUI();
    });
});

// Swap button
document.getElementById('h2h-swap-btn').addEventListener('click', function() {
    if (!selectedDriver1 || !selectedDriver2) return;
    [selectedDriver1, selectedDriver2] = [selectedDriver2, selectedDriver1];
    updateUI();
    runComparison();
});
