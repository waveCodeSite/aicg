"""
认证API集成测试
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.user import User


@pytest.mark.integration
class TestAuthAPI:
    """认证API测试类"""

    async def test_user_registration_success(self, client: AsyncClient, test_user_data: dict):
        """测试用户注册成功"""
        # 发送注册请求
        response = await client.post("/api/v1/auth/register", json=test_user_data)

        # 验证响应
        assert response.status_code == 201
        data = response.json()

        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert data["display_name"] == test_user_data["display_name"]
        assert "id" in data
        assert "created_at" in data
        assert data["is_active"] is True
        assert data["is_verified"] is False

    async def test_user_registration_duplicate_username(self, client: AsyncClient, test_user_data: dict):
        """测试用户注册 - 用户名重复"""
        # 先注册一个用户
        await client.post("/api/v1/auth/register", json=test_user_data)

        # 尝试用相同用户名再次注册
        response = await client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == 400
        assert "用户名已存在" in response.json()["detail"]

    async def test_user_registration_duplicate_email(self, client: AsyncClient, test_user_data: dict):
        """测试用户注册 - 邮箱重复"""
        # 先注册一个用户
        await client.post("/api/v1/auth/register", json=test_user_data)

        # 尝试用相同邮箱再次注册
        duplicate_data = test_user_data.copy()
        duplicate_data["username"] = "different_username"
        response = await client.post("/api/v1/auth/register", json=duplicate_data)

        assert response.status_code == 400
        assert "邮箱已存在" in response.json()["detail"]

    async def test_user_registration_invalid_data(self, client: AsyncClient):
        """测试用户注册 - 无效数据"""
        invalid_data = {
            "username": "",  # 空用户名
            "email": "invalid-email",  # 无效邮箱
            "password": "123",  # 密码太短
        }

        response = await client.post("/api/v1/auth/register", json=invalid_data)

        assert response.status_code == 422

    async def test_user_login_success(self, client: AsyncClient, test_user_data: dict):
        """测试用户登录成功"""
        # 先注册用户
        await client.post("/api/v1/auth/register", json=test_user_data)

        # 登录
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        response = await client.post("/api/v1/auth/login", data=login_data)

        # 验证响应
        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert "user" in data

        # 验证用户信息
        user_data = data["user"]
        assert user_data["username"] == test_user_data["username"]
        assert user_data["email"] == test_user_data["email"]

    async def test_user_login_invalid_credentials(self, client: AsyncClient, test_user_data: dict):
        """测试用户登录 - 无效凭据"""
        # 先注册用户
        await client.post("/api/v1/auth/register", json=test_user_data)

        # 使用错误密码登录
        login_data = {
            "username": test_user_data["username"],
            "password": "wrong_password"
        }
        response = await client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]

    async def test_user_login_nonexistent_user(self, client: AsyncClient):
        """测试用户登录 - 用户不存在"""
        login_data = {
            "username": "nonexistent_user",
            "password": "some_password"
        }
        response = await client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]

    async def test_get_current_user(self, client: AsyncClient, auth_headers: dict, test_user_data: dict):
        """测试获取当前用户信息"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert data["display_name"] == test_user_data["display_name"]
        assert data["is_active"] is True

    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """测试获取当前用户信息 - 未授权"""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """测试获取当前用户信息 - 无效token"""
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/v1/auth/me", headers=invalid_headers)

        assert response.status_code == 401

    async def test_logout_success(self, client: AsyncClient, auth_headers: dict):
        """测试登出成功"""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "登出成功"

    async def test_logout_unauthorized(self, client: AsyncClient):
        """测试登出 - 未授权"""
        response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 401

    async def test_verify_token_success(self, client: AsyncClient, auth_headers: dict):
        """测试验证token成功"""
        response = await client.get("/api/v1/auth/verify-token", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "user_id" in data
        assert "username" in data

    async def test_verify_token_invalid(self, client: AsyncClient):
        """测试验证token - 无效token"""
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/v1/auth/verify-token", headers=invalid_headers)

        assert response.status_code == 401

    async def test_user_password_hashing(self, db_session: AsyncSession, test_user_data: dict):
        """测试密码哈希存储"""
        from src.models.user import User

        # 创建用户
        user = await User.create_user(
            db_session=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
            display_name=test_user_data["display_name"]
        )

        # 验证密码已哈希存储
        assert user.password_hash is not None
        assert user.password_hash != test_user_data["password"]
        assert len(user.password_hash) > 50  # bcrypt哈希长度

    async def test_user_password_verification(self, db_session: AsyncSession, test_user_data: dict):
        """测试密码验证"""
        from src.models.user import User

        # 创建用户
        user = await User.create_user(
            db_session=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
            display_name=test_user_data["display_name"]
        )

        # 验证正确密码
        assert user.verify_password(test_user_data["password"]) is True

        # 验证错误密码
        assert user.verify_password("wrong_password") is False

    async def test_user_last_login_update(self, client: AsyncClient, test_user_data: dict, db_session: AsyncSession):
        """测试最后登录时间更新"""
        # 注册用户
        await client.post("/api/v1/auth/register", json=test_user_data)

        # 获取用户初始登录时间
        result = await db_session.execute(
            select(User).where(User.username == test_user_data["username"])
        )
        user = result.scalar_one()
        initial_last_login = user.last_login

        # 等待一小段时间确保时间差异
        import asyncio
        await asyncio.sleep(0.1)

        # 登录用户
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        await client.post("/api/v1/auth/login", data=login_data)

        # 验证最后登录时间已更新
        await db_session.refresh(user)
        if initial_last_login is None:
            # 如果初始last_login为None，现在应该不为None
            assert user.last_login is not None
        else:
            # 如果初始last_login不为None，现在应该更新
            assert user.last_login > initial_last_login

    async def test_jwt_token_invalid_token(self, client: AsyncClient):
        """测试无效JWT token被拒绝"""
        # 使用明显无效的token
        invalid_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.token"
        headers = {"Authorization": f"Bearer {invalid_token}"}

        response = await client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 401