from fastapi import APIRouter, Depends, BackgroundTasks, Request, HTTPException, status
from fastapi.responses import RedirectResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db_session
from ..services.short import ShortService

router_short = APIRouter(tags=["短链访问"])
router_short_api = APIRouter(prefix="/api/v1/short", tags=["短链管理"])


class ShortCreateRequest(BaseModel):
    long_url: str
    created_by: str = ""
    msg_context: str = ""
    length: int = 7


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


@router_short_api.post('')
async def create_short_url(
    payload: ShortCreateRequest,
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
):
    long_url = (payload.long_url or "").strip()
    if not long_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="long_url 必须以 http:// 或 https:// 开头",
        )
    if not (4 <= payload.length <= 32):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="length 需在 4~32 之间",
        )
    base = str(request.base_url)  # 形如 http://127.0.0.1:8000/
    record = await ShortService.create_short_url_auto(
        db_session,
        long_url=long_url,
        short_url_base=base,
        created_by=payload.created_by.strip(),
        msg_context=payload.msg_context.strip(),
        length=payload.length,
    )
    return {
        "code": "200",
        "msg": "短链生成成功",
        "data": {
            "id": record.id,
            "short_tag": record.short_tag,
            "short_url": record.short_url,
            "long_url": record.long_url,
            "visits_count": record.visits_count,
        },
    }