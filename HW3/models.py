from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel, HttpUrl
from typing import Optional

from database import Base

### база с зарегестрированными пользователями
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    links = relationship("Link", back_populates="owner")

### база ссылок
class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(Text, nullable=False)
    short_code = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    clicks = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    owner = relationship("User", back_populates="links")

### LinkCreate, LinkUpdate, LinkStats из main.py
class LinkCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None

class LinkUpdate(BaseModel):
    original_url: HttpUrl
    expires_at: Optional[datetime] = None

class LinkStats(BaseModel):
    original_url: str
    short_code: str
    created_at: datetime
    expires_at: datetime
    clicks: int
    last_used_at: Optional[datetime]
    is_active: bool
