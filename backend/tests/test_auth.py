import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_school(client: AsyncClient):
    response = await client.post("/api/auth/register", json={
        "school_name": "Test School",
        "school_code": "TEST001",
        "admin_email": "admin@test.com",
        "admin_password": "securepassword123",
        "admin_full_name": "Test Admin"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "admin"
    assert data["user"]["email"] == "admin@test.com"

@pytest.mark.asyncio
async def test_register_duplicate_school_code(client: AsyncClient):
    # Register first school
    await client.post("/api/auth/register", json={
        "school_name": "School A",
        "school_code": "DUP001",
        "admin_email": "admin1@test.com",
        "admin_password": "password123",
        "admin_full_name": "Admin One"
    })
    # Try duplicate code
    response = await client.post("/api/auth/register", json={
        "school_name": "School B",
        "school_code": "DUP001",
        "admin_email": "admin2@test.com",
        "admin_password": "password123",
        "admin_full_name": "Admin Two"
    })
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # Register
    await client.post("/api/auth/register", json={
        "school_name": "Login Test School",
        "school_code": "LOGIN01",
        "admin_email": "login@test.com",
        "admin_password": "password123",
        "admin_full_name": "Login Admin"
    })
    # Login
    response = await client.post("/api/auth/login", data={
        "username": "login@test.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "school_name": "Wrong PW School",
        "school_code": "WRONGPW",
        "admin_email": "wrong@test.com",
        "admin_password": "correctpassword",
        "admin_full_name": "Admin"
    })
    response = await client.post("/api/auth/login", data={
        "username": "wrong@test.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient):
    # Register and get token
    reg_response = await client.post("/api/auth/register", json={
        "school_name": "Me Test",
        "school_code": "ME001",
        "admin_email": "me@test.com",
        "admin_password": "password123",
        "admin_full_name": "Me Admin"
    })
    token = reg_response.json()["access_token"]
    
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@test.com"

@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    response = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
