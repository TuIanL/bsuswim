from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models import User
from app.schemas import UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return current_user
