from fastapi import FastAPI


app = FastAPI(title="Crypto Funding Arb")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
