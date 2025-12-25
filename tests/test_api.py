class TestHealthEndpoints:
    """Test basic application health."""

    def test_swagger_docs_available(self, client):
        """Swagger docs should be accessible."""
        response = client.get('/apidocs/')
        assert response.status_code == 200


class TestAPIEndpoints:
    """Test API endpoints return proper responses."""

    def test_data_endpoint_returns_json(self, client):
        """Data endpoint should return JSON."""
        response = client.get('/api/data')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_data_endpoint_pagination(self, client):
        """Data endpoint should support pagination parameters."""
        response = client.get('/api/data?page=1&per_page=10')
        assert response.status_code == 200
        data = response.get_json()
        assert 'total_results' in data
        assert 'current_page' in data
        assert 'per_page' in data

    def test_all_championship_wins_endpoint(self, client):
        """Championship wins endpoint should return JSON."""
        response = client.get('/api/all_championship_wins')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_highest_position_endpoint(self, client):
        """Highest position endpoint should return JSON."""
        response = client.get('/api/highest_position')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_min_races_to_win_endpoint(self, client):
        """Min races endpoint should return JSON."""
        response = client.get('/api/min_races_to_win')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_championship_win_probability_endpoint(self, client):
        """Probability endpoint should return JSON with expected structure."""
        response = client.get('/api/championship_win_probability')
        assert response.status_code == 200
        data = response.get_json()
        assert 'season_lengths' in data
        assert 'drivers_data' in data

    def test_driver_positions_requires_position(self, client):
        """Driver positions endpoint should require position parameter."""
        response = client.get('/api/driver_positions')
        assert response.status_code == 400

    def test_driver_positions_with_valid_position(self, client):
        """Driver positions endpoint should work with valid position."""
        response = client.get('/api/driver_positions?position=1')
        assert response.status_code == 200
        assert response.content_type == 'application/json'


class TestHeadToHead:
    """Test head-to-head comparison endpoint."""

    def test_head_to_head_same_driver_error(self, client):
        """Should error when comparing driver to themselves."""
        response = client.get('/api/head_to_head/VER/VER')
        assert response.status_code == 400

    def test_head_to_head_invalid_driver(self, client):
        """Should return 404 for unknown driver abbreviation."""
        response = client.get('/api/head_to_head/XXX/YYY')
        assert response.status_code == 404  # Unknown driver returns "not found"


class TestChampionshipEndpoints:
    """Test championship-specific endpoints."""

    def test_championship_not_found(self, client):
        """Should return 404 for non-existent championship."""
        response = client.get('/api/championship/999999999')
        assert response.status_code == 404

    def test_create_championship_no_rounds(self, client):
        """Should error when no rounds provided."""
        response = client.get('/api/create_championship')
        assert response.status_code == 400


class TestCacheEndpoint:
    """Test cache management."""

    def test_clear_cache(self, client):
        """Clear cache endpoint should work."""
        response = client.post('/api/clear_cache')
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
