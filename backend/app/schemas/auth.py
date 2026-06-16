from pydantic import BaseModel, Field

from app.models import UserRole


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=6, max_length=128)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    full_name: str | None = Field(default=None, max_length=80)
    role: UserRole | None = UserRole.COACH


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
