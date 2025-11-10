"""
pytest配置文件
"""

import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.main import app
from src.core.database import get_db_session
from src.models.base import Base

# 测试数据库URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# 创建测试引擎
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

# 创建测试会话工厂
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端"""
    from httpx import ASGITransport

    def override_get_db():
        return db_session

    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """测试用户数据"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "display_name": "测试用户"
    }


@pytest.fixture
def test_project_data():
    """测试项目数据"""
    return {
        "title": "测试项目",
        "description": "这是一个测试项目",
        "file_name": "test.txt",
        "file_type": "txt",
        "file_size": 1024
    }


@pytest.fixture
async def auth_headers(client: AsyncClient, test_user_data: dict):
    """获取认证头"""
    # 注册用户
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201

    # 登录获取token
    login_data = {
        "username": test_user_data["username"],
        "password": test_user_data["password"]
    }
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}