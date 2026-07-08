"""JSON API routers.

Endpoints are deliberately plain `def`, not `async def`: they run blocking
SQLAlchemy/SQLite calls, and sync endpoints get FastAPI's threadpool so one
slow query can't stall the event loop. Only switch a route to `async def`
if everything it awaits is genuinely non-blocking.
"""
