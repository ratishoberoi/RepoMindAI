from fastapi import FastAPI

from app.security import verify_token
from app.users import router as users_router

app = FastAPI(title="Sample Service")
app.include_router(users_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/admin")
def admin(token: str) -> dict[str, str]:
    verify_token(token)
    return {"area": "admin"}

