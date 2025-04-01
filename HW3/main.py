from fastapi import FastAPI, Depends, HTTPException, status, Request, Path
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime
import string, random, json
import redis.asyncio as redis
import re
from dotenv import load_dotenv
import os


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from models import User, Link, LinkCreate, LinkUpdate, LinkStats
from auth import (
    get_current_user,
    create_access_token,
    get_password_hash,
    verify_password,
)
from utils import (
    generate_short_code,
    strip_tz,
)

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 86400)) ### 1 день


app = FastAPI()
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

### ROUTES

@app.post("/register")
async def register(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=form_data.username,
        hashed_password=get_password_hash(form_data.password)
    )
    db.add(user)
    await db.commit()
    return {"msg": "User created"}

@app.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/links/shorten")
async def shorten_original_link(
    link: LinkCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    expires_at = strip_tz(link.expires_at)

    ### проверка даты истечения
    if expires_at and expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Expiration date must be in the future")

    # ### проверка на дубликат длинной ссылки
    # existing = await db.execute(
    #     select(Link).where(Link.original_url == str(link.original_url), Link.user_id == user.id)
    # )
    # if existing.scalars().first():
    #     raise HTTPException(status_code=400, detail="You already created a short link for this URL")

    ### проверка алиаса
    if link.custom_alias:
        if not re.match(r"^[a-zA-Z0-9_-]{3,30}$", link.custom_alias):
            raise HTTPException(status_code=400, detail="Invalid alias format or length")

        result = await db.execute(select(Link).where(Link.short_code == link.custom_alias))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Alias already taken")

        short_code = link.custom_alias
    # else:
    #     while True:
    #         short_code = generate_short_code()
    #         result = await db.execute(select(Link).where(Link.short_code == short_code))
    #         if not result.scalar_one_or_none():
    #             break
    else:
        max_attempts = 5
        for _ in range(max_attempts):
            generated_code = generate_short_code()
            existing = await db.execute(select(Link).where(Link.short_code == generated_code))
            if not existing.scalar_one_or_none():
                short_code = generated_code
                break
        else:
            raise HTTPException(status_code=500, detail="Failed to generate unique short code")


    original_url = str(link.original_url).strip().lower()

    new_link = Link(
        original_url=original_url,
        short_code=short_code,
        user_id=user.id if user else None,
        expires_at=expires_at,
        created_at=datetime.utcnow()
    )

    db.add(new_link)
    await db.commit()

    return {"short_url": f"{request.base_url}{short_code}"}



@app.get("/{short_code}")
async def redirect_short_link(
    short_code: str,
    db: AsyncSession = Depends(get_db)
):
    cache_key = f"short:{short_code}"
    cached_url = await r.get(cache_key)

    if cached_url:
        url = cached_url.decode()
    else:
        result = await db.execute(select(Link).where(Link.short_code == short_code))
        link = result.scalars().first()

        if not link:
            raise HTTPException(status_code=404, detail="Link not found")

        expires_at = strip_tz(link.expires_at)

        if expires_at and expires_at < datetime.utcnow():
            raise HTTPException(status_code=404, detail="Link has already expired")

        url = link.original_url
        await r.setex(cache_key, CACHE_TTL_SECONDS, url)
        link.clicks += 1
        link.last_used_at = datetime.utcnow()
        await db.commit()

    return RedirectResponse(url)

@app.put("/links/{short_code}")
async def update_short_link(
    short_code: str,
    data: LinkUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    new_expires_at = strip_tz(data.expires_at)

    if new_expires_at and new_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Expiration date must be in the future")

    result = await db.execute(
        select(Link).where((Link.short_code == short_code) & (Link.user_id == user.id))
    )
    link = result.scalars().first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    existing_expiry = strip_tz(link.expires_at)
    if existing_expiry and existing_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Link has already expired")

    link.original_url = str(data.original_url)
    link.expires_at = new_expires_at

    await db.commit()
    await r.delete(f"short:{short_code}")

    return {
        "message": "Link updated successfully",
        "short_code": short_code,
        "new_expires_at": link.expires_at
    }


@app.delete("/links/{short_code}")
async def delete_short_link(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(select(Link).where((Link.short_code == short_code) & (Link.user_id == user.id)))
    link = result.scalars().first()
    if not link:
        raise HTTPException(status_code=404, detail="Links not found")

    await db.delete(link)
    await db.commit()
    await r.delete(f"short:{short_code}")
    return {"msg": "Link deleted"}

@app.get("/links/{short_code}/stats", response_model=LinkStats)
async def stats_short_link(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(select(Link).where((Link.short_code == short_code) & (Link.user_id == user.id)))
    link = result.scalars().first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    now = datetime.utcnow()
    return LinkStats(
        original_url=link.original_url,
        short_code=link.short_code,
        created_at=link.created_at,
        expires_at=link.expires_at,
        clicks=link.clicks,
        last_used_at=link.last_used_at,
        expired=link.expires_at is not None and link.expires_at < now
    )

@app.get("/links/{original_url:path}/stats", response_model=List[LinkStats])
async def stats_original_link(
    original_url: str = Path(..., description="Original URL"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Link).where(Link.original_url == original_url, Link.user_id == user.id)
    )
    links = result.scalars().all()

    if not links:
        raise HTTPException(status_code=404, detail="No links found for this URL")

    now = datetime.utcnow()

    ### сортировка по кол-ву кликов
    sorted_links = sorted(links, key=lambda link: link.clicks, reverse=True)

    return [
        LinkStats(
            original_url=link.original_url,
            short_code=link.short_code,
            created_at=link.created_at,
            expires_at=link.expires_at,
            clicks=link.clicks,
            last_used_at=link.last_used_at,
            expired=link.expires_at is not None and link.expires_at < now
        )
        for link in sorted_links
    ]


@app.get("/links/search")
async def search_for_short_link(
    original_url: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Link).where(Link.original_url == original_url, Link.user_id == user.id)
    )
    links = result.scalars().all()

    if not links:
        raise HTTPException(status_code=404, detail="No links found for this URL")

    now = datetime.utcnow()

    links_with_expired = [
        {
            "short_code": link.short_code,
            "created_at": link.created_at,
            "expires_at": link.expires_at,
            "expired": link.expires_at is not None and link.expires_at < now
        }
        for link in links
    ]
    ### сначала неистекшие ссылки, а потом по дате создания
    sorted_links = sorted(links_with_expired, key=lambda x: (x["expired"], x["created_at"]))

    return sorted_links