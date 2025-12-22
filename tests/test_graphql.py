"""
Tests for the GraphQL API endpoints.
"""
import json


class TestGraphQLEndpoint:
    """Test GraphQL endpoint availability."""

    def test_graphql_endpoint_exists(self, client):
        """GraphQL endpoint should be accessible."""
        query = '{ __schema { types { name } } }'
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200


class TestGraphQLQueries:
    """Test GraphQL query operations."""

    def test_drivers_query(self, client):
        """Drivers query should return all drivers."""
        query = '''
        query {
            drivers {
                code
                name
                team
                number
                flag
                color
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        assert 'drivers' in data['data']
        assert len(data['data']['drivers']) == 20  # 20 drivers in models.py

    def test_driver_query(self, client):
        """Single driver query should work."""
        query = '''
        query {
            driver(code: "VER") {
                code
                name
                team
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['driver']['code'] == 'VER'
        assert data['data']['driver']['name'] == 'Max Verstappen'

    def test_driver_query_invalid_code(self, client):
        """Invalid driver code should return null."""
        query = '''
        query {
            driver(code: "INVALID") {
                code
                name
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['driver'] is None

    def test_championships_query(self, client):
        """Championships query should return paginated results."""
        query = '''
        query {
            championships(page: 1, perPage: 10) {
                totalResults
                currentPage
                perPage
                results {
                    championshipId
                    winner
                    numRaces
                }
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        assert 'championships' in data['data']
        assert 'totalResults' in data['data']['championships']
        assert 'currentPage' in data['data']['championships']

    def test_championship_by_id_query(self, client):
        """Single championship query should work."""
        query = '''
        query {
            championship(id: 1) {
                championshipId
                numRaces
                winner
                standings
                roundNames
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        # May be null if ID doesn't exist in test data
        if data['data']['championship']:
            assert 'championshipId' in data['data']['championship']

    def test_championship_wins_query(self, client):
        """Championship wins query should return results."""
        query = '''
        query {
            championshipWins {
                driverCode
                wins
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        assert 'championshipWins' in data['data']

    def test_highest_positions_query(self, client):
        """Highest positions query should work."""
        query = '''
        query {
            highestPositions {
                driver
                position
                championshipIds
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        assert 'highestPositions' in data['data']

    def test_min_races_to_win_query(self, client):
        """Min races to win query should work."""
        query = '''
        query {
            minRacesToWin {
                driverCode
                minRaces
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        assert 'minRacesToWin' in data['data']

    def test_driver_positions_query(self, client):
        """Driver positions query should work."""
        query = '''
        query {
            driverPositions(position: 1) {
                driver
                count
                percentage
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        assert 'driverPositions' in data['data']

    def test_championship_win_probability_query(self, client):
        """Championship win probability query should work."""
        query = '''
        query {
            championshipWinProbability {
                seasonLengths
                possibleSeasons
                driversData {
                    driver
                    totalTitles
                    percentages
                }
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        assert 'championshipWinProbability' in data['data']
        assert 'seasonLengths' in data['data']['championshipWinProbability']

    def test_driver_stats_query(self, client):
        """Driver stats query should work."""
        query = '''
        query {
            driverStats(driverCode: "VER") {
                driverCode
                driverName
                totalWins
                winPercentage
                highestPosition
                driverInfo {
                    team
                    number
                }
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        assert 'driverStats' in data['data']
        if data['data']['driverStats']:
            assert data['data']['driverStats']['driverCode'] == 'VER'

    def test_driver_stats_invalid_driver(self, client):
        """Driver stats should return null for invalid driver."""
        query = '''
        query {
            driverStats(driverCode: "INVALID") {
                driverCode
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['driverStats'] is None


class TestHeadToHead:
    """Test head-to-head comparison query."""

    def test_head_to_head_query(self, client):
        """Head to head comparison should work."""
        query = '''
        query {
            headToHead(driver1: "VER", driver2: "NOR") {
                driver1
                driver1Wins
                driver2
                driver2Wins
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        assert 'headToHead' in data['data']

    def test_head_to_head_same_driver_error(self, client):
        """Should error when comparing driver to themselves."""
        query = '''
        query {
            headToHead(driver1: "VER", driver2: "VER") {
                driver1Wins
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'errors' in data

    def test_head_to_head_invalid_driver(self, client):
        """Should error with invalid driver abbreviation."""
        query = '''
        query {
            headToHead(driver1: "XXX", driver2: "YYY") {
                driver1Wins
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'errors' in data


class TestFindChampionship:
    """Test find championship query."""

    def test_find_championship_no_rounds(self, client):
        """Should return error when no rounds provided."""
        query = '''
        query {
            findChampionship(rounds: []) {
                url
                error
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['findChampionship']['error'] is not None


class TestGraphQLMutations:
    """Test GraphQL mutation operations."""

    def test_clear_cache_mutation(self, client):
        """Clear cache mutation should work."""
        mutation = '''
        mutation {
            clearCache {
                success
                message
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': mutation}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['clearCache']['success'] is True
        assert 'message' in data['data']['clearCache']


class TestGraphQLComplexQueries:
    """Test more complex GraphQL query patterns."""

    def test_multiple_queries_in_one_request(self, client):
        """Should be able to run multiple queries in one request."""
        query = '''
        query {
            drivers {
                code
            }
            championshipWins {
                driverCode
                wins
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'drivers' in data['data']
        assert 'championshipWins' in data['data']

    def test_query_with_aliases(self, client):
        """Should support query aliases."""
        query = '''
        query {
            verstappen: driver(code: "VER") {
                name
                team
            }
            norris: driver(code: "NOR") {
                name
                team
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'verstappen' in data['data']
        assert 'norris' in data['data']
        assert data['data']['verstappen']['name'] == 'Max Verstappen'
        assert data['data']['norris']['name'] == 'Lando Norris'
