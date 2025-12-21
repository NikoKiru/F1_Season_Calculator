# API Reference

Complete documentation for the F1 Season Calculator REST API.

## Base URL

```
http://127.0.0.1:5000/api
```

## Interactive Documentation

Swagger UI is available at `/apidocs/` for interactive API exploration.

## Authentication

No authentication required. The API is open for local use.

## Response Format

All endpoints return JSON responses.

**Success Response**:
```json
{
  "data": { ... },
  "status": "success"
}
```

**Error Response**:
```json
{
  "error": "Error message",
  "status": "error"
}
```

---

## Endpoints

### GET /api/data

Retrieve championship data for a specific year.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `year` | integer | Yes | Championship year (1950-present) |

**Example Request**:
```bash
curl "http://127.0.0.1:5000/api/data?year=2024"
```

**Example Response**:
```json
{
  "year": 2024,
  "drivers": ["VER", "NOR", "LEC", ...],
  "races": ["Bahrain", "Saudi Arabia", ...],
  "results": [[25, 18, ...], ...],
  "points_system": [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
}
```

---

### GET /api/highest-position

Get the highest finishing position for each driver in a season.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `year` | integer | Yes | Championship year |

**Example Request**:
```bash
curl "http://127.0.0.1:5000/api/highest-position?year=2024"
```

**Example Response**:
```json
{
  "VER": 1,
  "NOR": 1,
  "LEC": 1,
  "SAI": 1,
  "PIA": 2
}
```

---

### GET /api/head-to-head

Get head-to-head comparison between two drivers.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `year` | integer | Yes | Championship year |
| `driver1` | string | Yes | First driver code (e.g., "VER") |
| `driver2` | string | Yes | Second driver code (e.g., "NOR") |

**Example Request**:
```bash
curl "http://127.0.0.1:5000/api/head-to-head?year=2024&driver1=VER&driver2=NOR"
```

**Example Response**:
```json
{
  "driver1": {
    "code": "VER",
    "wins": 15,
    "h2h_wins": 18,
    "total_points": 437
  },
  "driver2": {
    "code": "NOR",
    "wins": 4,
    "h2h_wins": 6,
    "total_points": 374
  },
  "races_compared": 24
}
```

---

### GET /api/driver-positions

Get position distribution for all drivers in a season.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `year` | integer | Yes | Championship year |

**Example Request**:
```bash
curl "http://127.0.0.1:5000/api/driver-positions?year=2024"
```

**Example Response**:
```json
{
  "VER": {
    "1": 9,
    "2": 6,
    "3": 2,
    "DNF": 2
  },
  "NOR": {
    "1": 4,
    "2": 5,
    "3": 4,
    "DNF": 1
  }
}
```

---

### GET /api/driver-stats

Get comprehensive statistics for all drivers in a season.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `year` | integer | Yes | Championship year |

**Example Request**:
```bash
curl "http://127.0.0.1:5000/api/driver-stats?year=2024"
```

**Example Response**:
```json
{
  "VER": {
    "total_points": 437,
    "wins": 9,
    "podiums": 17,
    "top_10": 22,
    "best_position": 1,
    "worst_position": 6,
    "avg_position": 2.3,
    "dnfs": 2,
    "sprint_points": 15
  }
}
```

---

### POST /api/clear-cache

Clear all API caches. Useful after data updates.

**Example Request**:
```bash
curl -X POST "http://127.0.0.1:5000/api/clear-cache"
```

**Example Response**:
```json
{
  "status": "success",
  "message": "Cache cleared"
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Missing or invalid parameters |
| 404 | Not Found - Year or driver not found |
| 500 | Internal Server Error |

## Rate Limiting

No rate limiting is applied for local use. For production deployments, consider implementing rate limiting at the reverse proxy level.

## Caching

API responses are cached in memory. Cache is automatically cleared when:
- Application restarts
- Data is refreshed via `flask process-data`
- `/api/clear-cache` is called

## Best Practices

1. **Cache Results Locally**: If making repeated calls, cache results in your application
2. **Handle Errors**: Always check for error responses
3. **Use Appropriate Endpoints**: Use specific endpoints rather than parsing general data
4. **Validate Year Parameter**: Ensure year is within valid range (1950-present)
