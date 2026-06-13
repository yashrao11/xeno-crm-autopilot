import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, text
from app.database import get_session, init_db
from app.routers import customers, analytics, campaigns, webhooks, ai_query

app = FastAPI(
    title="Xeno SmartReplenish AI CRM API",
    description="Predictive Replenishment and Marketing Automation CRM for retail/D2C brands.",
    version="1.0.0"
)

# Initialize Jinja2 templates directory
templates = Jinja2Templates(directory="app/templates")

# Startup event to ensure database tables are initialized
@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/", tags=["Dashboard"])
def render_dashboard(request: Request):
    return templates.TemplateResponse(request, "index.html")

# Health check route verifying database connectivity
@app.get("/health", tags=["Health"])
def health_check(session: Session = Depends(get_session)):
    try:
        # Execute simple query to test connection
        session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connectivity check failed: {str(e)}"
        )

# Register routers
app.include_router(customers.router)
app.include_router(analytics.router)
app.include_router(campaigns.router)
app.include_router(webhooks.router)
app.include_router(ai_query.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
