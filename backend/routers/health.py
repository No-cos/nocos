# routers/health.py
# Health check endpoint for the Nocos backend.
# Used by deployment platforms (Railway, Render) to verify the service is running.
# Also useful for local development to confirm the API is reachable.

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """
    Returns a simple status response to confirm the API is running.

    Used by load balancers and monitoring tools. If this endpoint returns
    anything other than 200, the deployment platform will restart the service.
    """
    return {"status": "ok"}
