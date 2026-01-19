"""
BioHIVE Backend API
Main FastAPI application with database integration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Import database initialization
from store import init_db

# Import routes
from routes import node_routes

# API configuration from Section 7.1
API_VERSION = os.getenv('API_VERSION', 'v1')
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',')

# Create FastAPI app
app = FastAPI(
    title="BioHIVE API",
    description="Disease surveillance system with decentralized data collection",
    version=API_VERSION,
    docs_url=f"/api/{API_VERSION}/docs",
    redoc_url=f"/api/{API_VERSION}/redoc"
)

# Configure CORS (Section 9 Pitfall 4)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database when app starts"""
    print("🚀 Starting BioHIVE API...")
    init_db()
    print(f"✅ API ready at /api/{API_VERSION}")


# Include routers
app.include_router(
    node_routes.router,
    prefix=f"/api/{API_VERSION}"
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint with database verification
    
    Checks:
    - API is running
    - Database is accessible
    - Audit trail integrity (optional)
    """
    from store import SessionLocal
    from schemas import Node
    
    health_status = {
        "status": "healthy",
        "service": "BioHIVE API",
        "version": API_VERSION,
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }
    
    # Check database connectivity
    try:
        db = SessionLocal()
        # Simple query to verify DB is accessible
        node_count = db.query(Node).count()
        health_status["database"] = {
            "status": "connected",
            "nodes": node_count
        }
        db.close()
    except Exception as e:
        health_status["database"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - redirect to docs"""
    return {
        "message": "BioHIVE API",
        "version": API_VERSION,
        "docs": f"/api/{API_VERSION}/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use 5000 as default
    port = int(os.getenv('PORT', '5000'))
    
    print(f"""
    ╔═══════════════════════════════════════╗
    ║         BioHIVE Backend API          ║
    ║     Disease Surveillance System       ║
    ╚═══════════════════════════════════════╝
    
    📡 API Base: http://localhost:{port}/api/{API_VERSION}
    📖 Docs:     http://localhost:{port}/api/{API_VERSION}/docs
    🏥 Health:   http://localhost:{port}/health
    
    Press CTRL+C to quit
    """)
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )