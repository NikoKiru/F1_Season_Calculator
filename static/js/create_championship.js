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
        window.location.href = `/api/create_championship?rounds=${roundsArray.join(',')}`;
    });
});
