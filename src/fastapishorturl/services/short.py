from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..models.model import ShortUrl


class ShortService:

    @staticmethod
    async def get_short_url(async_session: AsyncSession, short_tag: str):
        result = await async_session.execute(
            select(ShortUrl).where(ShortUrl.short_tag == short_tag)
        )
        return result.scalars().first()

    @staticmethod
    async def create_short_url(async_session: AsyncSession, **kwargs):
        new_short_url = ShortUrl(**kwargs)
        async_session.add(new_short_url)
        await async_session.commit()
        await async_session.refresh(new_short_url)  # 刷新获取自增ID
        return new_short_url

    @staticmethod
    async def update_short_url(async_session: AsyncSession, short_url_id: int, **kwargs):
        stmt = update(ShortUrl).where(ShortUrl.id == short_url_id).values(**kwargs)
        result = await async_session.execute(stmt)
        await async_session.commit()
        return result.rowcount  # 返回受影响行数

    @staticmethod
    async def delete_short_url(async_session: AsyncSession, short_url_id: int):
        stmt = delete(ShortUrl).where(ShortUrl.id == short_url_id)
        result = await async_session.execute(stmt)
        await async_session.commit()
        return result.rowcount  # 返回受影响行数

    @staticmethod
    async def create_batch_short_url(async_session: AsyncSession, short_urls: List[ShortUrl]):
        async_session.add_all(short_urls)
        await async_session.commit()
        return short_urls