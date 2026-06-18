import httpx
import os
from fastapi import HTTPException, Header
from typing import Optional

AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://auth-service:8001')

async def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token required")

    token = authorization.replace('Bearer ', '')

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/api/auth/verify/",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0
            )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")

        return response.json()

    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Auth service unavailable")