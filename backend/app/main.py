from fastapi import FastAPI

from app.api.v1 import files


app = FastAPI(title="FileFlow")
app.include_router(files.router, prefix="/api/v1")