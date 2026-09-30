from fastapi import FastAPI

from app.api.v1 import files, uploads


app = FastAPI(title="FileFlow")
app.include_router(files.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")