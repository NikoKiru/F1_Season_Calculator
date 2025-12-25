"""Tests for error handlers module."""
import pytest


class TestErrorHandlers:
    """Test error handlers."""

    def test_404_api_error(self, client):
        """API 404 should return JSON error."""
        response = client.get('/api/nonexistent')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert data['error']['code'] == 'NOT_FOUND'

    def test_404_view_error(self, client):
        """View 404 should return HTML page."""
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
        assert response.content_type.startswith('text/html')

    def test_405_api_error(self, client):
        """API 405 should return JSON error."""
        # POST to a GET-only endpoint
        response = client.post('/api/data')
        assert response.status_code == 405
        data = response.get_json()
        assert 'error' in data

    def test_400_validation_error(self, client):
        """Validation errors should return 400 with error details."""
        response = client.get('/api/driver_positions?position=invalid')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


class TestErrorResponseFormat:
    """Test error response format consistency."""

    def test_error_has_code(self, client):
        """All errors should have a code."""
        response = client.get('/api/driver/XXX/stats')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'code' in data['error']

    def test_error_has_message(self, client):
        """All errors should have a message."""
        response = client.get('/api/driver/XXX/stats')
        data = response.get_json()
        assert 'message' in data['error']

    def test_validation_error_has_field(self, client):
        """Validation errors should include field name."""
        response = client.get('/api/data?page=abc')
        assert response.status_code == 400
        data = response.get_json()
        assert 'field' in data['error']
        assert data['error']['field'] == 'page'
