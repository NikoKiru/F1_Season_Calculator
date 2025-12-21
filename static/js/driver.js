// Driver page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    loadDriverStats();
});

async function loadDriverStats() {
    try {
        const response = await fetch(`/api/driver/${DRIVER_CODE}/stats`);
        if (!response.ok) {
            throw new Error('Failed to load driver stats');
        }
        const data = await response.json();

        // Hide loading, show content
        document.getElementById('loading-indicator').style.display = 'none';
        document.getElementById('driver-content').style.display = 'block';

        // Populate stats cards
        populateStats(data);

        // Render charts
        renderPositionChart(data.position_distribution);
        renderProbabilityChart(data.win_probability_by_length, data.seasons_per_length);

        // Render head-to-head grid
        renderH2HGrid(data.head_to_head);

    } catch (error) {
        console.error('Error loading driver stats:', error);
        document.getElementById('loading-indicator').innerHTML = `
            <p style="color: var(--f1-red);">Error loading driver statistics. Please try again.</p>
        `;
    }
}

function populateStats(data) {
    // Total wins
    document.getElementById('stat-wins').textContent = formatNumber(data.total_wins);
    document.getElementById('stat-wins-pct').textContent = `${data.win_percentage}% of all scenarios`;

    // Best position
    document.getElementById('stat-best-pos').textContent = getOrdinal(data.highest_position);
    if (data.highest_position_championship_id) {
        document.getElementById('stat-best-link').innerHTML =
            `<a href="/championship/${data.highest_position_championship_id}">View example</a>`;
    }

    // Min races to win
    if (data.min_races_to_win) {
        document.getElementById('stat-min-races').textContent = data.min_races_to_win;
    } else {
        document.getElementById('stat-min-races').textContent = 'N/A';
        document.getElementById('stat-min-races').parentElement.querySelector('.stat-detail').textContent =
            'No championship wins';
    }

    // Win rate
    document.getElementById('stat-win-rate').textContent = `${data.win_percentage}%`;
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toLocaleString();
}

function getOrdinal(n) {
    const s = ["th", "st", "nd", "rd"];
    const v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function renderPositionChart(positionData) {
    const ctx = document.getElementById('position-chart').getContext('2d');

    // Create labels and data for positions 1-20
    const labels = [];
    const values = [];
    
    // Calculate total for percentage
    let total = 0;
    for (let i = 1; i <= 20; i++) {
        total += positionData[i] || 0;
    }
    
    for (let i = 1; i <= 20; i++) {
        labels.push(getOrdinal(i));
        const count = positionData[i] || 0;
        const percentage = total > 0 ? (count / total) * 100 : 0;
        values.push(percentage);
    }

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Position %',
                data: values,
                backgroundColor: TEAM_COLOR,
                borderColor: TEAM_COLOR,
                borderWidth: 1,
                borderRadius: 4
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
                            const value = context.raw;
                            return `${value.toFixed(1)}% of scenarios`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toFixed(0) + '%';
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function renderProbabilityChart(winProbData, seasonsPerLength) {
    const ctx = document.getElementById('probability-chart').getContext('2d');

    // Get all season lengths sorted
    const lengths = Object.keys(seasonsPerLength).map(Number).sort((a, b) => a - b);
    const probabilities = lengths.map(l => winProbData[l] || 0);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: lengths.map(l => `${l} races`),
            datasets: [{
                label: 'Win Probability %',
                data: probabilities,
                borderColor: TEAM_COLOR,
                backgroundColor: TEAM_COLOR + '33',
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointHoverRadius: 6
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
                            return `${context.raw.toFixed(2)}% win probability`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function renderH2HGrid(h2hData) {
    const grid = document.getElementById('h2h-grid');
    grid.innerHTML = '';

    // Sort opponents by win percentage descending
    const opponents = Object.keys(h2hData).sort((a, b) => {
        const totalA = h2hData[a].wins + h2hData[a].losses;
        const totalB = h2hData[b].wins + h2hData[b].losses;
        const pctA = totalA > 0 ? h2hData[a].wins / totalA : 0;
        const pctB = totalB > 0 ? h2hData[b].wins / totalB : 0;
        return pctB - pctA;
    });

    opponents.forEach(opponentCode => {
        const record = h2hData[opponentCode];
        const opponent = DRIVERS[opponentCode];

        if (!opponent) return;

        const wins = record.wins;
        const losses = record.losses;
        const total = wins + losses;
        
        // Calculate percentages
        const winPct = total > 0 ? ((wins / total) * 100).toFixed(0) : 0;
        const lossPct = total > 0 ? ((losses / total) * 100).toFixed(0) : 0;

        let statusClass = 'tied';
        if (wins > losses) statusClass = 'winning';
        else if (losses > wins) statusClass = 'losing';

        const card = document.createElement('div');
        card.className = `h2h-card ${statusClass}`;
        card.innerHTML = `
            <span class="h2h-opponent">${opponent.flag} ${opponent.name.split(' ').pop()}</span>
            <span class="h2h-record">
                <span class="wins">${winPct}%</span> -
                <span class="losses">${lossPct}%</span>
            </span>
        `;

        grid.appendChild(card);
    });
}
