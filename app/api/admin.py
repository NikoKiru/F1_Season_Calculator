from fastapi import APIRouter

from app.cache import service as cache_service


router = APIRouter()


@router.post("/clear-cache", status_code=204)
async def clear_cache() -> None:
    cache_service.clear()
