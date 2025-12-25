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


class TestHighestPositionEnriched:
    """Test enriched highest position endpoint."""

    def test_highest_position_returns_enriched_data(self, client):
        """Highest position should return enriched data structure."""
        response = client.get('/api/highest_position')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        if len(data) > 0:
            item = data[0]
            assert 'driver' in item
            assert 'position' in item
            assert 'max_races' in item
            assert 'best_margin' in item or item.get('best_margin') is None

    def test_highest_position_sorted_by_position(self, client):
        """Results should be sorted by position."""
        response = client.get('/api/highest_position')
        data = response.get_json()
        positions = [item['position'] for item in data]
        assert positions == sorted(positions)

    def test_highest_position_margin_for_winners(self, client):
        """Winners (position 1) should have margin data."""
        response = client.get('/api/highest_position')
        data = response.get_json()
        winners = [item for item in data if item['position'] == 1]
        # All winners should have margin and championship_id
        for winner in winners:
            assert winner['best_margin'] is not None
            assert winner['best_margin'] >= 0
            assert winner['best_margin_championship_id'] is not None

    def test_highest_position_non_winners_no_margin(self, client):
        """Non-winners should not have margin data."""
        response = client.get('/api/highest_position')
        data = response.get_json()
        non_winners = [item for item in data if item['position'] > 1]
        for non_winner in non_winners:
            assert non_winner['best_margin'] is None


class TestHighestPositionView:
    """Test highest position view page."""

    def test_highest_position_page_loads(self, client):
        """Highest position page should load successfully."""
        response = client.get('/highest_position')
        assert response.status_code == 200
        assert b'Highest Championship Position' in response.data


class TestDriverPositionChampionships:
    """Test driver position championships endpoint."""

    def test_driver_position_valid_request(self, client):
        """Should return championships for valid driver and position."""
        response = client.get('/api/driver/VER/position/1')
        assert response.status_code == 200
        data = response.get_json()
        assert 'driver_code' in data
        assert 'position' in data
        assert 'total_count' in data
        assert 'championships' in data
        assert data['driver_code'] == 'VER'
        assert data['position'] == 1

    def test_driver_position_invalid_driver(self, client):
        """Should return 404 for unknown driver."""
        response = client.get('/api/driver/XXX/position/1')
        assert response.status_code == 404

    def test_driver_position_invalid_position(self, client):
        """Should return 400 for invalid position."""
        response = client.get('/api/driver/VER/position/0')
        assert response.status_code == 400
        response = client.get('/api/driver/VER/position/25')
        assert response.status_code == 400

    def test_driver_position_championship_data_structure(self, client):
        """Championships should have expected structure."""
        response = client.get('/api/driver/VER/position/1')
        data = response.get_json()
        if data['total_count'] > 0:
            champ = data['championships'][0]
            assert 'championship_id' in champ
            assert 'num_races' in champ
            assert 'standings' in champ
            assert 'driver_points' in champ
            assert 'margin' in champ or champ.get('margin') is None

    def test_driver_position_pagination_fields(self, client):
        """Response should include pagination fields."""
        response = client.get('/api/driver/VER/position/1')
        data = response.get_json()
        assert 'page' in data
        assert 'per_page' in data
        assert 'total_pages' in data
        assert data['page'] == 1
        assert data['per_page'] == 100

    def test_driver_position_custom_pagination(self, client):
        """Should respect custom pagination parameters."""
        response = client.get('/api/driver/VER/position/1?page=1&per_page=10')
        data = response.get_json()
        assert data['per_page'] == 10
        assert len(data['championships']) <= 10


class TestDriverPositionDetailView:
    """Test driver position detail view."""

    def test_driver_position_detail_page_loads(self, client):
        """Driver position detail page should load."""
        response = client.get('/driver/VER/position/1')
        assert response.status_code == 200
        assert b'VER' in response.data or b'Verstappen' in response.data

    def test_driver_position_detail_invalid_driver(self, client):
        """Should return 404 for unknown driver."""
        response = client.get('/driver/XXX/position/1')
        assert response.status_code == 404

    def test_driver_position_detail_case_insensitive(self, client):
        """Driver code should be case insensitive."""
        response = client.get('/driver/ver/position/1')
        assert response.status_code == 200
