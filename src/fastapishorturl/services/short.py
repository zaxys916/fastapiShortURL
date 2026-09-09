from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

import secrets
import string

from ..models.model import ShortUrl


def generate_short_url(prefix: str = "", length: int = 7) -> str:
    """生成随机短码（字母+数字，不含易混淆字符）"""
    alphabet = string.ascii_letters + string.digits
    return prefix + ''.join(secrets.choice(alphabet) for _ in range(length))


class ShortService:

    @staticmethod
    async def get_short_url(async_session: AsyncSession, short_tag: str):
        result = await async_session.execute(
            select(ShortUrl).where(ShortUrl.short_tag == short_tag)
        )
        return result.scalars().first()

    @staticmethod
    async def create_short_url_auto(
        async_session: AsyncSession,
        long_url: str,
        short_url_base: str,
        created_by: str = "",
        msg_context: str = "",
        length: int = 7,
    ):
        """自动生成唯一短码并创建短链，返回新记录"""
        while True:
            short_tag = generate_short_url(length=length)
            exist = await ShortService.get_short_url(async_session, short_tag)
            if not exist:
                break
        new_short_url = ShortUrl(
            short_tag=short_tag,
            short_url=f"{short_url_base}{short_tag}",
            long_url=long_url,
            visits_count=0,
            created_by=created_by,
            msg_context=msg_context,
        )
        async_session.add(new_short_url)
        await async_session.commit()
        await async_session.refresh(new_short_url)
        return new_short_url

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