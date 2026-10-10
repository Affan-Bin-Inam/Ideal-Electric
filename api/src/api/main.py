from fastapi import FastAPI
from sqlalchemy import text

from api.deps import DbSession
from api.routers import auth, catalogue, products

app = FastAPI(title="Ideal Electric API", version="0.1.0")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
async def health_check_db(db: DbSession):
    result = await db.execute(text("SELECT version()"))
    return {"status": "ok", "postgres_version": result.scalar_one()}


app.include_router(catalogue.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")