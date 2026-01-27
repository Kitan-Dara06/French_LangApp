from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import questions
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)
app = FastAPI()

app.include_router(questions.router, prefix="/api")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def home():
    return FileResponse("static/index.html")


def root():
    return {"message": "Hello World"}
