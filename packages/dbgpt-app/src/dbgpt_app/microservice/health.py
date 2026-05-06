from __future__ import annotations

from fastapi import FastAPI


def mount_health_routes(app: FastAPI, version: str) -> None:
    @app.get("/api/health", tags=["Health"])
    async def health():
        return {
            "status": "ok",
            "service": "dbgpt-webserver",
            "version": version,
        }
