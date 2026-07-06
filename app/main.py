from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import auth, classes, modules, rubrics, groups, discussions, tasks, submissions, users, quests

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PBL SmartHub AI - Backend API",
    description=(
        "Backend FastAPI untuk platform manajemen pembelajaran PBL/PjBL "
        "dengan AI Agent (Gemini) sesuai PRD PBL SmartHub AI."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(classes.router)
app.include_router(modules.router)
app.include_router(rubrics.router)
app.include_router(groups.router)
app.include_router(discussions.router)
app.include_router(tasks.router)
app.include_router(submissions.router)
app.include_router(users.router)
app.include_router(quests.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "PBL SmartHub AI backend is running"}
