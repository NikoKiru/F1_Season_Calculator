document.getElementById('h2h-form').addEventListener('submit', function(event) {
    event.preventDefault();
    const driver1 = document.getElementById('driver1').value.trim();
    const driver2 = document.getElementById('driver2').value.trim();
    const resultDiv = document.getElementById('h2h-result');

    if (driver1 && driver2) {
        fetch(`/api/head_to_head/${driver1}/${driver2}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.error || 'Server error'); });
                }
                return response.json();
            })
            .then(data => {
                const d1Code = Object.keys(data)[0];
                const d2Code = Object.keys(data)[1];
                const d1Data = DRIVERS[d1Code] || {};
                const d2Data = DRIVERS[d2Code] || {};

                resultDiv.innerHTML = `
                    <div class="driver-result" style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <span class="color-bar" style="background-color: ${d1Data.color || '#666'}; width: 4px; height: 24px; border-radius: 2px;"></span>
                        <span>${d1Data.name || d1Code}: <strong>${Object.values(data)[0]}</strong> wins</span>
                    </div>
                    <div class="driver-result" style="display: flex; align-items: center; gap: 10px;">
                        <span class="color-bar" style="background-color: ${d2Data.color || '#666'}; width: 4px; height: 24px; border-radius: 2px;"></span>
                        <span>${d2Data.name || d2Code}: <strong>${Object.values(data)[1]}</strong> wins</span>
                    </div>
                `;
            })
            .catch(error => {
                console.error('Error fetching H2H data:', error);
                resultDiv.innerHTML = `<p class="driver-result">Error: ${error.message}</p>`;
            });
    }
});
