"""FastAPI application entry point for Everest Textile Mills ERP."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mill.database import Base, engine
from mill.routers.auth import router as auth_router
from mill.routers.items import router as items_router
from mill.routers.partners import router as partners_router
from mill.routers.purchasing import router as purchasing_router
from mill.routers.orders import router as orders_router
from mill.routers.machines import router as machines_router
from mill.routers.production import router as production_router
from mill.routers.rolls import router as rolls_router
from mill.routers.dispatch import router as dispatch_router
from mill.routers.finance import router as finance_router
from mill.routers.attendance import router as attendance_router, wages_router
from mill.routers.dashboard import dashboard_router, costing_router, settings_router

# Create all tables (development convenience; use Alembic for production migrations)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Everest Textile Mills ERP",
    description="Unified ERP for yarn intake, production, QC, dispatch, attendance, wages, costing and payments.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(items_router)
app.include_router(partners_router)
app.include_router(purchasing_router)
app.include_router(orders_router)
app.include_router(machines_router)
app.include_router(production_router)
app.include_router(rolls_router)
app.include_router(dispatch_router)
app.include_router(finance_router)
app.include_router(attendance_router)
app.include_router(wages_router)
app.include_router(dashboard_router)
app.include_router(costing_router)
app.include_router(settings_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "mill": "Everest Textile Mills"}
