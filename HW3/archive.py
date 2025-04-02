from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from datetime import datetime
from database import async_session
from models import Link

#
async def archive_expired_links():
    async with async_session() as session:
        await _archive_expired(session)


async def _archive_expired(session: AsyncSession):
    now = datetime.utcnow()
    stmt = (
        update(Link)
        .where(Link.expires_at != None)
        .where(Link.expires_at < now)
        .where(Link.is_active == True)
        .values(is_active=False)
    )
    await session.execute(stmt)
    await session.commit()
