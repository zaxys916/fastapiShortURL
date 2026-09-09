from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.model import User


class UserService:

    @staticmethod
    async def get_by_name(async_session: AsyncSession, username: str) -> User | None:
        result = await async_session.execute(
            select(User).where(User.username == username)
        )
        return result.scalars().first()

    @staticmethod
    async def get_by_id(async_session: AsyncSession, user_id: int) -> User | None:
        result = await async_session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalars().first()

    @staticmethod
    async def create_user(
        async_session: AsyncSession, username: str, password_hash: str
    ) -> User:
        user = User(username=username, password=password_hash)
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        return user