from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db_session
from ..services.short import ShortService

router_short = APIRouter(tags=["短链访问"])


@router_short.get('/{short_tag}')
async def short_redirect(
    *,
    short_tag: str,
    db_session: AsyncSession = Depends(get_db_session),
    tasks: BackgroundTasks
):
    data = await ShortService.get_short_url(db_session, short_tag)
    if not data:
        return PlainTextResponse("没有对应短链信息记录")
    
    # 更新访问次数（使用 BackgroundTasks 异步执行）
    data.visits_count = data.visits_count + 1
    tasks.add_task(
        ShortService.update_short_url,
        db_session,
        short_url_id=data.id,
        visits_count=data.visits_count
    )
    
    return RedirectResponse(url=data.long_url)