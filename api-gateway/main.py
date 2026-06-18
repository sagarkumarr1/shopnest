from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ShopNest API Gateway",
    description="Single entry point for all ShopNest microservices",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
AUTH_URL = os.environ.get('AUTH_SERVICE_URL', 'http://localhost:8001')
PRODUCT_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://localhost:8002')
NOTIFICATION_URL = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://localhost:8003')


async def proxy_request(request: Request, target_url: str) -> JSONResponse:
    """Forward request to target service."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Forward headers
        headers = dict(request.headers)
        headers.pop('host', None)

        # Forward body
        body = await request.body()

        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=dict(request.query_params)
        )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code
        )


# ── HEALTH CHECK ──
@app.get("/health")
async def health():
    services = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in [
            ("auth", AUTH_URL),
            ("product", PRODUCT_URL),
            ("notification", NOTIFICATION_URL),
        ]:
            try:
                r = await client.get(f"{url}/health")
                services[name] = "healthy" if r.status_code == 200 else "unhealthy"
            except:
                services[name] = "unreachable"

    all_healthy = all(s == "healthy" for s in services.values())
    return {
        "gateway": "healthy",
        "services": services,
        "status": "ok" if all_healthy else "degraded"
    }


# ── AUTH ROUTES ──
@app.api_route("/api/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def auth_proxy(path: str, request: Request):
    try:
        return await proxy_request(request, f"{AUTH_URL}/api/auth/{path}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Auth service timeout")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Auth service error: {str(e)}")


# ── PRODUCT ROUTES ──
@app.api_route("/api/products/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def product_proxy(path: str, request: Request):
    try:
        return await proxy_request(request, f"{PRODUCT_URL}/api/products/{path}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Product service timeout")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Product service error: {str(e)}")

@app.api_route("/api/products", methods=["GET", "POST"])
async def products_proxy(request: Request):
    try:
        return await proxy_request(request, f"{PRODUCT_URL}/api/products/")
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Product service timeout")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Product service error: {str(e)}")


# ── NOTIFICATION ROUTES ──
@app.api_route("/api/notifications/{path:path}", methods=["GET", "POST"])
async def notification_proxy(path: str, request: Request):
    try:
        return await proxy_request(request, f"{NOTIFICATION_URL}/api/notifications/{path}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Notification service timeout")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Notification service error: {str(e)}")


# ── ROOT ──
@app.get("/")
async def root():
    return {
        "message": "ShopNest API Gateway 🚀",
        "version": "1.0.0",
        "services": {
            "auth": "/api/auth/",
            "products": "/api/products/",
            "notifications": "/api/notifications/",
        },
        "health": "/health",
        "docs": "/docs"
    }