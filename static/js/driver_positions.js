const slider = document.getElementById('position-slider');
const resultsDiv = document.getElementById('results');
const positionHeader = document.getElementById('position-header');

let abortController = new AbortController();
let debounceTimer;

function debounce(func, delay) {
    return function(...args) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}

async function fetchData(position) {
    // Abort any ongoing fetch request
    abortController.abort();
    abortController = new AbortController();
    const signal = abortController.signal;

    resultsDiv.innerHTML = '<p>Loading...</p>';
    positionHeader.textContent = `Position: ${position}`;
    try {
        const response = await fetch(`/api/driver_positions?position=${position}`, { signal });
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        
        if (signal.aborted) {
            return; // Don't update the DOM if the request was aborted
        }

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
                    <span class="driver-name">${name}</span>
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
            resultsDiv.innerHTML = `<p>Error fetching data: ${error.message}</p>`;
        }
    }
}

const debouncedFetchData = debounce(fetchData, 200);

slider.addEventListener('input', () => {
    const position = slider.value;
    positionHeader.textContent = `Position: ${position}`;
    debouncedFetchData(position);
});

// Initial data load
fetchData(slider.value);
