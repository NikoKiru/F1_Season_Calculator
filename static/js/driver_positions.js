const resultsDiv = document.getElementById('results');
const positionHeader = document.getElementById('position-header');
const loadingIndicator = document.getElementById('loading-indicator');
const podiumBlocks = document.querySelectorAll('.podium-block');
const positionBtns = document.querySelectorAll('.position-btn');

let abortController = new AbortController();
let currentPosition = null;

function getPositionSuffix(pos) {
    if (pos === 1) return 'st';
    if (pos === 2) return 'nd';
    if (pos === 3) return 'rd';
    return 'th';
}

function setActivePosition(position) {
    // Remove active class from all buttons
    podiumBlocks.forEach(block => block.classList.remove('active'));
    positionBtns.forEach(btn => btn.classList.remove('active'));

    // Add active class to clicked button
    const podiumBlock = document.querySelector(`.podium-block[data-position="${position}"]`);
    const positionBtn = document.querySelector(`.position-btn[data-position="${position}"]`);

    if (podiumBlock) podiumBlock.classList.add('active');
    if (positionBtn) positionBtn.classList.add('active');
}

async function fetchData(position) {
    // Abort any ongoing fetch request
    abortController.abort();
    abortController = new AbortController();
    const signal = abortController.signal;

    currentPosition = position;
    setActivePosition(position);

    // Show loading, hide results
    loadingIndicator.style.display = 'block';
    resultsDiv.innerHTML = '';
    positionHeader.textContent = `Position: ${position}${getPositionSuffix(position)}`;

    try {
        const response = await fetch(`/api/driver_positions?position=${position}&season=${CURRENT_SEASON}`, { signal });
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();

        if (signal.aborted) {
            return; // Don't update the DOM if the request was aborted
        }

        // Hide loading
        loadingIndicator.style.display = 'none';

        if (Object.keys(data).length === 0) {
            resultsDiv.innerHTML = '<p>No data available for this position.</p>';
            return;
        }

        let html = '<ul class="driver-list">';
        for (const item of data) {
            const driverData = DRIVERS[item.driver] || {};
            const color = driverData.color || '#666';
            const name = driverData.name || item.driver;
            const team = driverData.team || '';
            html += `<li>
                <span class="team-color-stripe" style="background-color: ${color};"></span>
                <div class="driver-info">
                    <a href="/driver/${item.driver}?season=${CURRENT_SEASON}" class="driver-name">${name}</a>
                    <span class="driver-team">${team}</span>
                </div>
                <span class="driver-wins">${item.count} times (${item.percentage}%)</span>
            </li>`;
        }
        html += '</ul>';
        resultsDiv.innerHTML = html;

    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Fetch aborted');
        } else {
            loadingIndicator.style.display = 'none';
            resultsDiv.innerHTML = `<p>Error fetching data: ${error.message}</p>`;
        }
    }
}

// Add click handlers to podium blocks
podiumBlocks.forEach(block => {
    block.addEventListener('click', () => {
        const position = parseInt(block.dataset.position);
        fetchData(position);
    });
});

// Add click handlers to position buttons
positionBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const position = parseInt(btn.dataset.position);
        fetchData(position);
    });
});
