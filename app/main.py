from fastapi import FastAPI

from app.routers.auth import router as auth_router

app = FastAPI(
    title="Public Pulse API",
    version="0.1.0",
)

@app.get("/health")
def health_check() -> dict[str,str]:
    return {'status':'healthy'}

app.include_router(auth_router)