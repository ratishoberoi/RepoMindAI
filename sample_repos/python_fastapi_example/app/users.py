from fastapi import APIRouter

router = APIRouter(prefix="/users")


@router.get("/{user_id}")
def read_user(user_id: int) -> dict[str, int]:
    return {"user_id": user_id}

