from fastapi import FastAPI
from .api.user import router_user
from .api.short import router_short

app = FastAPI(title='fastapi集成短链服务')

@app.on_event("startup")
async def startup_event():
    from .db.database import async_engine, Base
    from .models.model import User, ShortUrl  # 导入模型确保注册
    
    async def init_create_table():
        async with async_engine.begin() as conn:
            # 生产环境建议使用 Alembic 迁移，而非 drop_all
            # await conn.run_sync(Base.metadata.drop_all)  # 危险！会删除所有数据
            await conn.run_sync(Base.metadata.create_all)
    
    await init_create_table()

@app.on_event("shutdown")
async def shutdown_event():
    from .db.database import async_engine
    await async_engine.dispose()  # 释放数据库连接池


app.include_router(router_user)
app.include_router(router_short)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app='main:app', host="127.0.0.1", port=8000, reload=True)