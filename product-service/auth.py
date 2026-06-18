from typing import Optional

import httpx
import os

from fastapi import Header, HTTPException


AUTH_SERVICE_URL = os.environ.get(
    "AUTH_SERVICE_URL",
    "http://localhost:8001"
)


async def verify_token(
    authorization: Optional[str] = Header(None)
):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format"
        )

    token = authorization.replace("Bearer ", "").strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Token required"
        )

    try:
        async with httpx.AsyncClient(
            timeout=5.0
        ) as client:

            response = await client.get(
                f"{AUTH_SERVICE_URL}/api/auth/verify/",
                headers={
                    "Authorization": f"Bearer {token}"
                }
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        user_data = response.json()

        if not isinstance(user_data, dict):
            raise HTTPException(
                status_code=500,
                detail="Invalid auth service response"
            )

        return user_data

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail="Auth service timeout"
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Auth service unavailable"
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Authentication failed"
        )