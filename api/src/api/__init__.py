# from fastapi import Depends, FastAPI

# from sqlalchemy import text
# from sqlalchemy.ext.asyncio import AsyncSession

# from api.db import get_db

# app = FastAPI(title="Ideal Electric API")


# @app.get("/health")
# def health_check():
#     return {"status": "ok"}

# @app.get("/health/db")
# async def health_check_db(db: AsyncSession = Depends(get_db)):
#     result = await db.execute(text("SELECT version()"))
#     version = result.scalar_one()
#     return {"status": "ok", "postgres_version": version}