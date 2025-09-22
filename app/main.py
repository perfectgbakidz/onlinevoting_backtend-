import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import users, elections, admin, superadmin, auditor, audit_logs, auth as auth_router
from .database import engine, Base, SessionLocal
from . import models
from passlib.context import CryptContext

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS or ["*"],  # configure properly in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Routers ---
app.include_router(auth_router.router)
app.include_router(users.router)
app.include_router(elections.router)
app.include_router(admin.router)
app.include_router(superadmin.router)
app.include_router(auditor.router)
app.include_router(audit_logs.router)


# --- Root endpoint ---
@app.get("/", tags=["Health"])
def root():
    return {
        "message": "NACOS E-Voting API - Production-ready scaffold",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


# --- Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    print("🚀 Application startup - NACOS E-Voting API ready")

    # Ensure default superadmin exists
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter_by(role="superadmin").first()
        if not admin:
            hashed_password = pwd_context.hash("admin123")
            super_admin = models.User(
                name="Super Admin",
                email="superadmin@nacos.com",
                student_id="NACOS-0000",
                level=None,
                course=None,
                hashed_password=hashed_password,
                role="superadmin"
            )
            db.add(super_admin)
            db.commit()
            print("✅ Default superadmin created: superadmin@nacos.com / admin123")
        else:
            print("ℹ️ Superadmin already exists")
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Application shutdown")


# --- Run with uvicorn (dev only, not for gunicorn/production) ---
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
