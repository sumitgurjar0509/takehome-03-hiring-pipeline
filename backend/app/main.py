from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import applications, auth, dashboard, openings, panel

settings = get_settings()

app = FastAPI(title="Hiring Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(openings.router)
app.include_router(applications.opening_applications_router)
app.include_router(applications.applications_router)
app.include_router(panel.router)
app.include_router(dashboard.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
