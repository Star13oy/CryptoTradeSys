from fastapi import FastAPI

from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.scan import router as scan_router


app = FastAPI(title="Crypto Funding Arb")
app.include_router(dashboard_router)
app.include_router(scan_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
