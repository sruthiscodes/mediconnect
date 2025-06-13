from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.api.routes import triage, auth, history
from app.core.config import settings

load_dotenv()

app = FastAPI(
    title="MediConnect Healthcare Triage API",
    description="AI-powered healthcare triage and care navigation platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(triage.router, prefix="/api/triage", tags=["triage"])
app.include_router(history.router, prefix="/api/history", tags=["history"])

@app.get("/")
async def root():
    return {"message": "MediConnect Healthcare Triage API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 