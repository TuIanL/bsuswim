"""Create the local development coach account when it is missing."""

import os

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models import User, UserRole


USERNAME = os.getenv("DEV_USERNAME", "coach_demo")
PASSWORD = os.getenv("DEV_PASSWORD", "coach_demo123")


def main() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == USERNAME))
        if user is None:
            db.add(User(
                username=USERNAME,
                password_hash=get_password_hash(PASSWORD),
                full_name="演示教练",
                role=UserRole.COACH,
                is_active=True,
            ))
            db.commit()
            print(f"created development user: {USERNAME}")
        else:
            print(f"development user exists: {USERNAME}")


if __name__ == "__main__":
    main()
