"""Create a user from the command line:  uv run python -m api.create_admin"""
import asyncio
import getpass

from sqlalchemy import select

from api.db import async_session_factory, engine
from api.models import User
from api.security import hash_password

ROLES = ("admin", "editor", "sales")


async def main() -> None:
    email = input("Email: ").strip().lower()
    full_name = input("Full name: ").strip()
    role = input(f"Role {ROLES} [admin]: ").strip() or "admin"
    if role not in ROLES:
        raise SystemExit(f"Role must be one of {ROLES}.")
    password = getpass.getpass("Password (at least 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password is too short.")
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match.")

    async with async_session_factory() as session:
        existing = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            raise SystemExit("A user with that email already exists.")
        session.add(
            User(email=email, full_name=full_name, role=role, password_hash=hash_password(password))
        )
        await session.commit()
    await engine.dispose()
    print(f"Created {role} user {email}.")


if __name__ == "__main__":
    asyncio.run(main())