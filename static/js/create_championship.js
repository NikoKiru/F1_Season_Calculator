document.getElementById('search-form').addEventListener('submit', function(event) {
    event.preventDefault();
    const championshipId = document.getElementById('search-input').value;
    if (championshipId) {
        window.location.href = `/championship/${championshipId}`;
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const raceGrid = document.getElementById('race-grid');
    const generateButton = document.getElementById('generate-championship');
    const randomButton = document.getElementById('random-races');
    const selectedRounds = new Set();

    raceGrid.addEventListener('click', function(event) {
        const target = event.target;
        if (target.classList.contains('race-block')) {
            const roundNumber = target.dataset.roundNumber;
            if (selectedRounds.has(roundNumber)) {
                selectedRounds.delete(roundNumber);
                target.classList.remove('selected');
            } else {
                selectedRounds.add(roundNumber);
                target.classList.add('selected');
            }
        }
    });

    generateButton.addEventListener('click', function() {
        if (selectedRounds.size === 0) {
            alert('Please select at least one race.');
            return;
        }
        const roundsArray = Array.from(selectedRounds);
        
        const url = `/api/create_championship?rounds=${roundsArray.join(',')}`;

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.error || 'Server error'); });
                }
                return response.json();
            })
            .then(data => {
                if (data.url) {
                    window.location.href = data.url;
                } else {
                    alert('Could not find championship.');
                }
            })
            .catch(error => {
                alert(`Error: ${error.message}`);
            });
    });

    randomButton.addEventListener('click', function() {
        // Clear existing selections
        selectedRounds.clear();
        const allRaces = raceGrid.querySelectorAll('.race-block');
        allRaces.forEach(race => {
            race.classList.remove('selected');
            if (Math.random() < 0.5) {
                const roundNumber = race.dataset.roundNumber;
                selectedRounds.add(roundNumber);
                race.classList.add('selected');
            }
        });

        // Ensure at least one race is selected
        if (selectedRounds.size === 0 && allRaces.length > 0) {
            const randomIndex = Math.floor(Math.random() * allRaces.length);
            const randomRace = allRaces[randomIndex];
            const roundNumber = randomRace.dataset.roundNumber;
            selectedRounds.add(roundNumber);
            randomRace.classList.add('selected');
        }
    });
});
