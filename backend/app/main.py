from fastapi import FastAPI

app = FastAPI(title="FileFlow")

@app.get("/")
def root():
    return {"message": "FileFlow API"}