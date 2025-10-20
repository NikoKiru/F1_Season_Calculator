const positionInput = document.getElementById('position-input');
const decreaseBtn = document.getElementById('decrease-pos');
const increaseBtn = document.getElementById('increase-pos');
const resultsDiv = document.getElementById('results');
const positionHeader = document.getElementById('position-header');

async function fetchData(position) {
    resultsDiv.innerHTML = '<p>Loading...</p>';
    positionHeader.textContent = `Position: ${position}`;
    try {
        const response = await fetch(`/api/driver_positions?position=${position}`);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        
        if (Object.keys(data).length === 0) {
            resultsDiv.innerHTML = '<p>No data available for this position.</p>';
            return;
        }

        let html = '<ul class="driver-list">';
        for (const item of data) {
            html += `<li><span class="driver-name">${item.driver}</span> <span class="driver-wins">${item.count} times (${item.percentage}%)</span></li>`;
        }
        html += '</ul>';
        resultsDiv.innerHTML = html;

    } catch (error) {
        resultsDiv.innerHTML = `<p>Error fetching data: ${error.message}</p>`;
    }
}

function updatePosition(change) {
    let currentPos = parseInt(positionInput.value);
    currentPos += change;
    if (currentPos < 1) currentPos = 1;
    if (currentPos > 20) currentPos = 20;
    positionInput.value = currentPos;
    fetchData(currentPos);
}

decreaseBtn.addEventListener('click', () => updatePosition(-1));
increaseBtn.addEventListener('click', () => updatePosition(1));
positionInput.addEventListener('change', () => {
    let pos = parseInt(positionInput.value);
    if (pos < 1) pos = 1;
    if (pos > 20) pos = 20;
    positionInput.value = pos;
    fetchData(pos);
});

// Initial data load
fetchData(positionInput.value);
