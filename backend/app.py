from fastapi import FastAPI

from backend.config import BASE_PATH
from backend.services.response import success

from backend.routes.node_routes import router as node_router
from backend.routes.dashboard_routes import router as dashboard_router
from backend.routes.auth_routes import router as auth_router

app = FastAPI()

@app.get("/health")
def health_check():
    return success({"status": "ok"}, "BioHIVE backend running")

@app.get(f"{BASE_PATH}/health")
def api_health_check():
    return success({"status": "ok"}, "API v1 running")

app.include_router(node_router, prefix=BASE_PATH)
app.include_router(dashboard_router, prefix=BASE_PATH)
app.include_router(auth_router, prefix=BASE_PATH)
