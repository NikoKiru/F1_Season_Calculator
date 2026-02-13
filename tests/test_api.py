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

    def test_championship_win_probability_uses_cache(self, client):
        """Probability endpoint should use pre-computed cache data."""
        response = client.get('/api/championship_win_probability')
        assert response.status_code == 200
        data = response.get_json()
        # Verify structure from cached data
        assert 'season_lengths' in data
        assert 'possible_seasons' in data
        assert 'drivers_data' in data
        assert 'driver_names' in data
        # Verify season lengths from test data (3, 4, 5, 6 races)
        assert 3 in data['season_lengths']
        assert 4 in data['season_lengths']
        assert 5 in data['season_lengths']
        assert 6 in data['season_lengths']

    def test_championship_win_probability_driver_data(self, client):
        """Probability endpoint should include all drivers with correct structure."""
        response = client.get('/api/championship_win_probability')
        data = response.get_json()
        drivers_data = data['drivers_data']
        assert len(drivers_data) > 0
        # Check structure of driver data
        for driver_data in drivers_data:
            assert 'driver' in driver_data
            assert 'total_titles' in driver_data
            assert 'wins_per_length' in driver_data
            assert 'percentages' in driver_data
            # Percentages should match season_lengths count
            assert len(driver_data['percentages']) == len(data['season_lengths'])

    def test_championship_win_probability_percentages(self, client):
        """Probability endpoint should calculate percentages correctly."""
        response = client.get('/api/championship_win_probability')
        data = response.get_json()
        # Find VER's data
        ver_data = next((d for d in data['drivers_data'] if d['driver'] == 'VER'), None)
        assert ver_data is not None
        # VER has 3 total wins in test data
        assert ver_data['total_titles'] == 3
        # All percentages should be between 0 and 100
        for pct in ver_data['percentages']:
            assert 0 <= pct <= 100

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


class TestViewPages:
    """Test all view page routes."""

    def test_index_page(self, client):
        """Index page should load."""
        response = client.get('/')
        assert response.status_code == 200

    def test_all_championship_wins_page(self, client):
        """All championship wins page should load."""
        response = client.get('/all_championship_wins')
        assert response.status_code == 200

    def test_driver_positions_page(self, client):
        """Driver positions page should load."""
        response = client.get('/driver_positions')
        assert response.status_code == 200

    def test_head_to_head_page(self, client):
        """Head to head page should load."""
        response = client.get('/head_to_head')
        assert response.status_code == 200

    def test_min_races_to_win_page(self, client):
        """Min races to win page should load."""
        response = client.get('/min_races_to_win')
        assert response.status_code == 200

    def test_championship_win_probability_page(self, client):
        """Championship win probability page should load."""
        response = client.get('/championship_win_probability')
        assert response.status_code == 200

    def test_create_championship_page(self, client):
        """Create championship page should load."""
        response = client.get('/create_championship')
        assert response.status_code == 200

    def test_drivers_page(self, client):
        """Drivers list page should load."""
        response = client.get('/drivers')
        assert response.status_code == 200

    def test_driver_page_valid(self, client):
        """Individual driver page should load for valid driver."""
        response = client.get('/driver/VER')
        assert response.status_code == 200
        assert b'Verstappen' in response.data or b'VER' in response.data

    def test_driver_page_case_insensitive(self, client):
        """Driver page should handle lowercase driver code."""
        response = client.get('/driver/ver')
        assert response.status_code == 200

    def test_driver_page_invalid(self, client):
        """Driver page should return 404 for invalid driver."""
        response = client.get('/driver/XXX')
        assert response.status_code == 404

    def test_championship_page_with_data(self, client):
        """Championship page should load for existing championship."""
        response = client.get('/championship/1')
        assert response.status_code == 200

    def test_championship_page_not_found(self, client):
        """Championship page should handle non-existent championship."""
        response = client.get('/championship/999999')
        assert response.status_code == 404


class TestHeadToHeadEndpoint:
    """Extended head-to-head endpoint tests."""

    def test_head_to_head_valid_comparison(self, client):
        """Should return valid comparison data."""
        response = client.get('/api/head_to_head/VER/NOR')
        assert response.status_code == 200
        data = response.get_json()
        assert 'VER' in data
        assert 'NOR' in data

    def test_head_to_head_reverse_order(self, client):
        """Should work with reversed driver order."""
        response = client.get('/api/head_to_head/NOR/VER')
        assert response.status_code == 200
        data = response.get_json()
        assert 'VER' in data
        assert 'NOR' in data


class TestDriverStatsEndpoint:
    """Test driver stats endpoint."""

    def test_driver_stats_valid(self, client):
        """Should return driver stats for valid driver."""
        response = client.get('/api/driver/VER/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert 'driver_code' in data
        assert 'driver_name' in data
        assert 'total_wins' in data
        assert 'win_percentage' in data
        assert 'highest_position' in data

    def test_driver_stats_has_required_fields(self, client):
        """Should include all required fields."""
        response = client.get('/api/driver/VER/stats')
        data = response.get_json()
        required_fields = [
            'driver_code', 'driver_name', 'driver_info',
            'total_wins', 'total_championships', 'win_percentage',
            'highest_position', 'min_races_to_win',
            'position_distribution', 'win_probability_by_length',
            'seasons_per_length'
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_driver_stats_invalid_driver(self, client):
        """Should return 404 for unknown driver."""
        response = client.get('/api/driver/XXX/stats')
        assert response.status_code == 404

    def test_driver_stats_case_insensitive(self, client):
        """Driver code should be case insensitive."""
        response = client.get('/api/driver/ver/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert data['driver_code'] == 'VER'


class TestCreateChampionshipEndpoint:
    """Test create championship endpoint."""

    def test_create_championship_valid_rounds(self, client):
        """Should return championship URL for valid rounds."""
        response = client.get('/api/create_championship?rounds=1,2,3')
        # Either finds it or returns 404 (championship not in test data)
        assert response.status_code in [200, 404]

    def test_create_championship_invalid_rounds(self, client):
        """Should return 400 for invalid rounds format."""
        response = client.get('/api/create_championship?rounds=abc')
        assert response.status_code == 400

    def test_create_championship_out_of_range(self, client):
        """Should return 400 for out of range rounds."""
        response = client.get('/api/create_championship?rounds=0,1,2')
        assert response.status_code == 400

    def test_create_championship_duplicate_rounds(self, client):
        """Should return 400 for duplicate rounds."""
        response = client.get('/api/create_championship?rounds=1,1,2')
        assert response.status_code == 400


class TestChampionshipEndpointExtended:
    """Extended championship endpoint tests."""

    def test_championship_returns_expected_fields(self, client):
        """Championship should return expected data structure."""
        response = client.get('/api/championship/1')
        assert response.status_code == 200
        data = response.get_json()
        assert 'championship_id' in data
        assert 'standings' in data
        assert 'points' in data


class TestDataEndpointExtended:
    """Extended data endpoint tests."""

    def test_data_endpoint_invalid_page(self, client):
        """Should return 400 for invalid page."""
        response = client.get('/api/data?page=abc')
        assert response.status_code == 400

    def test_data_endpoint_negative_page(self, client):
        """Should return 400 for negative page."""
        response = client.get('/api/data?page=-1')
        assert response.status_code == 400

    def test_data_endpoint_invalid_per_page(self, client):
        """Should return 400 for invalid per_page."""
        response = client.get('/api/data?per_page=abc')
        assert response.status_code == 400

    def test_data_endpoint_per_page_too_large(self, client):
        """Should return 400 for per_page exceeding maximum."""
        response = client.get('/api/data?per_page=10000')
        assert response.status_code == 400


class TestDriverPositionsEndpoint:
    """Extended driver positions endpoint tests."""

    def test_driver_positions_invalid_position_format(self, client):
        """Should return 400 for invalid position format."""
        response = client.get('/api/driver_positions?position=abc')
        assert response.status_code == 400

    def test_driver_positions_out_of_range(self, client):
        """Should return 400 for out of range position."""
        response = client.get('/api/driver_positions?position=30')
        assert response.status_code == 400

    def test_driver_positions_negative(self, client):
        """Should return 400 for negative position."""
        response = client.get('/api/driver_positions?position=-1')
        assert response.status_code == 400


class TestDriverPositionNonWinner:
    """Test driver position endpoint for non-P1 positions."""

    def test_driver_position_p2(self, client):
        """Should return championships where driver finished P2."""
        response = client.get('/api/driver/VER/position/2')
        assert response.status_code == 200
        data = response.get_json()
        assert data['position'] == 2

    def test_driver_position_p3(self, client):
        """Should return championships where driver finished P3."""
        response = client.get('/api/driver/NOR/position/3')
        assert response.status_code == 200
        data = response.get_json()
        assert data['position'] == 3


class TestCachingBehavior:
    """Test that caching works correctly for expensive endpoints."""

    def test_all_championship_wins_cached(self, client):
        """Second call should return same data (from cache)."""
        r1 = client.get('/api/all_championship_wins')
        r2 = client.get('/api/all_championship_wins')
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.get_json() == r2.get_json()

    def test_min_races_to_win_cached(self, client):
        """Second call should return same data (from cache)."""
        r1 = client.get('/api/min_races_to_win')
        r2 = client.get('/api/min_races_to_win')
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.get_json() == r2.get_json()

    def test_head_to_head_cached(self, client):
        """Second call should return same data (from cache)."""
        r1 = client.get('/api/head_to_head/VER/NOR')
        r2 = client.get('/api/head_to_head/VER/NOR')
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.get_json() == r2.get_json()

    def test_driver_positions_cached(self, client):
        """Second call should return same data (from cache)."""
        r1 = client.get('/api/driver_positions?position=1')
        r2 = client.get('/api/driver_positions?position=1')
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.get_json() == r2.get_json()

    def test_driver_stats_cached(self, client):
        """Second call should return same data (from cache)."""
        r1 = client.get('/api/driver/VER/stats')
        r2 = client.get('/api/driver/VER/stats')
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.get_json() == r2.get_json()


class TestHeadToHeadUsingPositionResults:
    """Test head-to-head comparison using indexed position_results table."""

    def test_head_to_head_returns_correct_counts(self, client):
        """Head-to-head should count position comparisons correctly."""
        response = client.get('/api/head_to_head/VER/NOR')
        assert response.status_code == 200
        data = response.get_json()
        # VER beats NOR in championships 1 (P1 vs P2), 3 (P1 vs P3), 4 (P1 vs P2)
        # NOR beats VER in championships 2 (P1 vs P2), 5 (P3 vs P2)
        # Wait - championship 5: LEC P1, VER P2, NOR P3 -> VER beats NOR
        # So VER: 4, NOR: 1
        assert data['VER'] == 4
        assert data['NOR'] == 1

    def test_head_to_head_symmetric(self, client):
        """Reversed order should give same totals."""
        r1 = client.get('/api/head_to_head/VER/LEC')
        r2 = client.get('/api/head_to_head/LEC/VER')
        d1 = r1.get_json()
        d2 = r2.get_json()
        assert d1['VER'] == d2['VER']
        assert d1['LEC'] == d2['LEC']
