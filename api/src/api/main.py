import mimetypes #-------------------------> GPT suggession

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from api.deps import DbSession
from api.routers import (
    admin_attachments, admin_categories, admin_inquiries, admin_media, admin_products, admin_site_settings,
    admin_taxonomy, auth, catalogue, inquiries, products, site_settings, homepage, admin_homepage
)
from api.services.storage import storage

# Ensure WebP files are served with the correct MIME type.
mimetypes.add_type("image/webp", ".webp") #-------------------------> GPT suggession

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
app.include_router(site_settings.router, prefix="/api/v1")   # new, public
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin_categories.router, prefix="/api/v1")
app.include_router(admin_taxonomy.router, prefix="/api/v1")
app.include_router(admin_products.router, prefix="/api/v1")
app.include_router(admin_site_settings.router, prefix="/api/v1")   # new, admin
app.include_router(inquiries.router, prefix="/api/v1")
app.include_router(admin_inquiries.router, prefix="/api/v1")

# In development the files are served from the local folder. With R2 the browser fetches them
# straight from the bucket and this mount goes away.
app.mount(storage.url_prefix, StaticFiles(directory=storage.root), name="media")
app.include_router(admin_media.router, prefix="/api/v1")
app.include_router(admin_attachments.router, prefix="/api/v1")
app.include_router(homepage.router, prefix="/api/v1")
app.include_router(admin_homepage.router, prefix="/api/v1")