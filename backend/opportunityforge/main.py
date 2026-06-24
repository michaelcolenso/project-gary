from fastapi import FastAPI

from opportunityforge.api.routes import router

app = FastAPI(
    title="OpportunityForge API",
    description="Public-data business opportunity intelligence API.",
    version="0.1.0",
)
app.include_router(router, prefix="/api")
