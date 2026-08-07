from fastapi import FastAPI

app = FastAPI(
    title="Version-Aware Documentation Assistant",
    description="A documentation QA service that isolates answers by product version.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "version-aware-doc-assistant",
    }