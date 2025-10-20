document.getElementById('search-form').addEventListener('submit', function(event) {
    event.preventDefault();
    const championshipId = document.getElementById('search-input').value;
    if (championshipId) {
        window.location.href = `/championship/${championshipId}`;
    }
});
