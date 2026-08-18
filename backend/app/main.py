from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, health, users, transactions, mpesa
from app.core.config import get_settings

s=get_settings()
app=FastAPI(title="Sugercane API",version="0.1.0",docs_url="/docs" if s.app_env!="production" else None,redoc_url="/redoc" if s.app_env!="production" else None)
if s.origins:
    app.add_middleware(CORSMiddleware,allow_origins=s.origins,allow_credentials=True,allow_methods=["GET","POST","PUT","PATCH","DELETE"],allow_headers=["Content-Type","X-CSRF-Token"])
app.include_router(health.router,prefix="/api"); app.include_router(auth.router,prefix="/api"); app.include_router(users.router,prefix="/api"); app.include_router(transactions.router, prefix="/api");
app.include_router(
    mpesa.router,
    prefix="/api"
)
