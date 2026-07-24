from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
app = FastAPI(
    title="Public Pulse API",
    version="0.1.0",
)

@app.get("/health")
def health_check() -> dict[str,str]:
    """
    Here we are just confirming that the API server is running
    """
    return {'status':'healthy'}

app.include_router(auth_router)
app.include_router(users_router)