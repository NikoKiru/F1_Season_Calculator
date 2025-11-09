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
                resultDiv.innerHTML = `
                    <p class="driver-result">${Object.keys(data)[0]}: ${Object.values(data)[0]} wins</p>
                    <p class="driver-result">${Object.keys(data)[1]}: ${Object.values(data)[1]} wins</p>
                `;
            })
            .catch(error => {
                console.error('Error fetching H2H data:', error);
                resultDiv.innerHTML = `<p class="driver-result">Error: ${error.message}</p>`;
            });
    }
});
