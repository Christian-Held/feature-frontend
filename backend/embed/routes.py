"""Routes serving the public embed chat experience."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.rag.models.website import Website

router = APIRouter(prefix="/embed", tags=["embed"])

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _serialize_website(website: Website) -> dict[str, Any]:
    return {
        "name": website.name or "AI Assistant",
        "brand_color": website.brand_color or "#2563eb",
        "logo_url": website.logo_url,
        "welcome_message": website.welcome_message
        or "Hi! How can I help you today?",
        "position": website.position.value,
        "language": website.language,
        "token": website.embed_token,
    }


@router.get("/chat", response_class=HTMLResponse, include_in_schema=False)
def embed_chat(
    request: Request,
    token: str = Query(..., alias="token"),
    session: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the embedded chat experience for a given website token."""
    result = session.execute(
        select(Website).where(
            Website.embed_token == token,
            Website.is_active.is_(True),
        )
    )
    website = result.scalar_one_or_none()

    if website is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat experience not found",
        )

    website_config = _serialize_website(website)

    response = templates.TemplateResponse(
        "embed_chat.html",
        {
            "request": request,
            "website": website_config,
        },
    )

    response.headers["Cache-Control"] = "no-store"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@router.get("/config", response_class=JSONResponse, include_in_schema=False)
def embed_config(
    token: str = Query(..., alias="token"),
    session: Session = Depends(get_db),
) -> JSONResponse:
    result = session.execute(
        select(Website).where(
            Website.embed_token == token,
            Website.is_active.is_(True),
        )
    )
    website = result.scalar_one_or_none()

    if website is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat experience not found",
        )

    payload = _serialize_website(website)
    response = JSONResponse(payload)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "X-Embed-Token, Content-Type"
    return response


__all__ = ["router"]
