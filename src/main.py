from fastapi import FastAPI
from src.api.routes import router

app = FastAPI(title="Valura AI Microservice")
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}