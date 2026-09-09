from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from ..dependencies import get_db_session
from ..services.user import UserService
from ..utils.passlib_hepler import PasslibHelper
from ..utils.auth_helper import AuthTokenHelper

logger = logging.getLogger(__name__)

router_user = APIRouter(
    prefix="/api/v1",
    tags=["用户认证管理"],
    responses={
        400: {"description": "请求参数错误"},
        401: {"description": "认证失败"},
        500: {"description": "服务器内部错误"}
    }
)

# OAuth2 密码流配置
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/oauth2/authorize",
    auto_error=True
)


# ==================== 0. 用户注册 ====================
@router_user.post(
    "/user/register",
    summary="用户注册",
    description="创建新用户",
    response_model=Dict[str, Any]
)
async def register(
    user_data: Dict[str, Any] = Body(...),
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    用户注册接口

    Args:
        user_data: 请求体，需包含 username 和 password
        db_session: 数据库会话

    Returns:
        创建成功的用户信息
    """
    username = (user_data.get("username") or "").strip()
    password = user_data.get("password") or ""

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请输入用户名和密码"
        )

    # 检查用户名唯一性
    exist = await UserService.get_by_name(db_session, username)
    if exist:
        logger.warning(f"注册失败，用户名已存在: {username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 加密后入库
    password_hash = PasslibHelper.hash_password(password)
    user = await UserService.create_user(db_session, username, password_hash)
    logger.info(f"用户注册成功: {username} (ID: {user.id})")

    return {
        "code": "200",
        "msg": "注册成功",
        "data": {
            "id": user.id,
            "username": user.username
        }
    }


# ==================== 1. 用户登录 ====================
@router_user.post(
    "/oauth2/authorize",
    summary="用户登录授权",
    description="使用用户名和密码获取访问令牌",
    response_model=Dict[str, Any]
)
async def login(
    user_data: OAuth2PasswordRequestForm = Depends(),
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    用户登录接口
    
    Args:
        user_data: OAuth2 表单数据（包含 username 和 password）
        db_session: 数据库会话
    
    Returns:
        包含 access_token 和 token_type 的响应
    """
    # 1. 验证请求数据
    if not user_data.username or not user_data.password:
        logger.warning("登录请求缺少用户名或密码")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请输入用户账号及密码"
        )
    
    # 2. 查询用户是否存在
    userinfo = await UserService.get_by_name(db_session, user_data.username)
    if not userinfo:
        logger.warning(f"登录失败，用户不存在: {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",  # 统一提示，避免信息泄露
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 3. 验证用户密码
    if not PasslibHelper.verify_password(user_data.password, userinfo.password):
        logger.warning(f"登录失败，密码错误: {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",  # 统一提示
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 4. 检查用户是否被禁用
    if not getattr(userinfo, 'is_active', True):
        logger.warning(f"登录失败，用户已被禁用: {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用，请联系管理员"
        )
    
    # 5. 签发 JWT Token
    try:
        # Access Token（短期）
        access_token_data = {
            'iss': 'short_url_service',
            'sub': str(userinfo.id),
            'username': userinfo.username,
            'is_admin': getattr(userinfo, 'is_admin', False),
            'type': 'access',
            'exp': datetime.utcnow() + timedelta(minutes=30)
        }
        
        access_token = AuthTokenHelper.token_encode(access_token_data)
        
        # Refresh Token（长期，用于刷新 Access Token）
        refresh_token_data = {
            'iss': 'short_url_service',
            'sub': str(userinfo.id),
            'type': 'refresh',
            'exp': datetime.utcnow() + timedelta(days=7)  # 7天有效期
        }
        refresh_token = AuthTokenHelper.token_encode(refresh_token_data)
        
        logger.info(f"用户登录成功: {userinfo.username} (ID: {userinfo.id})")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 1800,  # 30分钟
            "username": userinfo.username,
            "user_id": userinfo.id
        }
        
    except Exception as e:
        logger.error(f"Token 生成失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器内部错误，请稍后重试"
        )


# ==================== 2. 刷新 Token ====================
@router_user.post(
    "/oauth2/refresh",
    summary="刷新访问令牌",
    description="使用 Refresh Token 获取新的 Access Token",
    response_model=Dict[str, Any]
)
async def refresh_token(
    refresh_token: str,
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    使用刷新令牌获取新的访问令牌
    
    Args:
        refresh_token: 刷新令牌字符串
        db_session: 数据库会话
    
    Returns:
        新的访问令牌
    """
    try:
        # 解码并验证 Refresh Token
        payload = AuthTokenHelper.token_decode(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌"
            )
        
        # 验证 Token 类型
        if payload.get('type') != 'refresh':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌类型"
            )
        
        # 获取用户信息
        user_id = int(payload.get('sub'))
        userinfo = await UserService.get_by_id(db_session, user_id)
        if not userinfo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )
        
        if not getattr(userinfo, 'is_active', True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用"
            )
        
        # 生成新的 Access Token
        new_token_data = {
            'iss': 'short_url_service',
            'sub': str(userinfo.id),
            'username': userinfo.username,
            'is_admin': getattr(userinfo, 'is_admin', False),
            'type': 'access',
            'exp': datetime.utcnow() + timedelta(minutes=30)
        }
        
        new_access_token = AuthTokenHelper.token_encode(new_token_data)
        
        logger.info(f"Token 刷新成功: {userinfo.username} (ID: {userinfo.id})")
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": 1800
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刷新 Token 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效或已过期"
        )


# ==================== 3. 获取当前用户信息 ====================
@router_user.get(
    "/user/me",
    summary="获取当前用户信息",
    description="获取当前登录用户的详细信息（需要认证）",
    response_model=Dict[str, Any]
)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    获取当前登录用户的信息
    
    Args:
        token: 访问令牌
        db_session: 数据库会话
    
    Returns:
        当前用户信息
    """
    try:
        # 解码 Token
        payload = AuthTokenHelper.token_decode(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的访问令牌"
            )
        
        # 验证 Token 类型
        if payload.get('type') != 'access':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的访问令牌类型"
            )
        
        # 获取用户信息
        username = payload.get('username')
        userinfo = await UserService.get_by_name(db_session, username)
        if not userinfo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )
        
        return {
            "code": "200",
            "data": {
                "id": userinfo.id,
                "username": userinfo.username,
                "email": getattr(userinfo, 'email', None),
                "is_admin": getattr(userinfo, 'is_admin', False),
                "is_active": getattr(userinfo, 'is_active', True),
                "created_at": getattr(userinfo, 'created_at', None)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取当前用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的访问令牌"
        )


# ==================== 4. 用户登出 ====================
@router_user.post(
    "/oauth2/logout",
    summary="用户登出",
    description="注销当前用户的登录状态",
    response_model=Dict[str, str]
)
async def logout(
    token: str = Depends(oauth2_scheme)
):
    """
    用户登出接口
    
    Args:
        token: 访问令牌
    
    Returns:
        登出成功消息
    
    Note:
        实际项目中建议将 Token 加入黑名单或 Redis 缓存
    """
    try:
        # 解码 Token
        payload = AuthTokenHelper.token_decode(token)
        if payload:
            username = payload.get('username')
            logger.info(f"用户登出: {username}")
        
        # TODO: 将 Token 加入黑名单（Redis）
        # 示例：redis_client.setex(f"blacklist:{token}", 1800, "1")
        
        return {
            "code": "200",
            "msg": "登出成功"
        }
    except Exception as e:
        logger.error(f"登出失败: {e}")
        return {
            "code": "200",
            "msg": "登出成功"
        }


# ==================== 5. 验证 Token 有效性 ====================
@router_user.post(
    "/oauth2/verify",
    summary="验证 Token 有效性",
    description="检查访问令牌是否有效",
    response_model=Dict[str, Any]
)
async def verify_token(
    token: str = Depends(oauth2_scheme),
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    验证 Token 是否有效
    
    Args:
        token: 访问令牌
        db_session: 数据库会话
    
    Returns:
        Token 验证结果
    """
    try:
        payload = AuthTokenHelper.token_decode(token)
        if not payload:
            return {
                "code": "401",
                "valid": False,
                "detail": "无效的访问令牌"
            }
        
        # 验证 Token 类型
        if payload.get('type') != 'access':
            return {
                "code": "401",
                "valid": False,
                "detail": "无效的访问令牌类型"
            }
        
        # 检查用户是否存在
        username = payload.get('username')
        userinfo = await UserService.get_by_name(db_session, username)
        if not userinfo:
            return {
                "code": "401",
                "valid": False,
                "detail": "用户不存在"
            }
        
        return {
            "code": "200",
            "valid": True,
            "data": {
                "username": username,
                "user_id": payload.get('sub'),
                "is_admin": payload.get('is_admin', False)
            }
        }
        
    except Exception as e:
        logger.error(f"验证 Token 失败: {e}")
        return {
            "code": "500",
            "valid": False,
            "detail": "服务器内部错误"
        }