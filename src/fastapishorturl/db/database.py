# 导入异步引擎的模块
import os

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine import make_url

# URL地址格式
from ..config.config import get_settings, PROJECT_ROOT

# 将相对路径的 SQLite 地址锚定到项目根(main.py 所在目录)，避免受启动目录(cwd)影响
_settings = get_settings()
_parsed = make_url(_settings.ASYNC_DATABASE_URL)
_db_url = _settings.ASYNC_DATABASE_URL
if _parsed.drivername.startswith("sqlite") and _parsed.database != ":memory:":
    # 兼容 sqlite:///path 与 sqlite://dir/path 两种相对写法
    db_file = "/".join(part for part in (_parsed.host or "", _parsed.database or "") if part)
    if db_file and not os.path.isabs(db_file):
        _db_url = f"sqlite+aiosqlite:///{(PROJECT_ROOT / db_file).as_posix()}"

# 创建异步引擎对象
async_engine = create_async_engine(_db_url, echo=False)

# 创建ORM模型基类
Base = declarative_base()

# 创建异步的会话工厂管理对象
SessionLocal = sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)