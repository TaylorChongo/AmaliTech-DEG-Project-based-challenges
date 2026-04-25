import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from main import app, monitors, GRACE_PERIOD

@pytest.fixture(autouse=True)
def clear_monitors():
    """Clear the in-memory monitors dictionary before each test."""
    monitors.clear()
    yield

@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Pulse Check API running"}

@pytest.mark.asyncio
async def test_register_monitor():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/monitors", json={
            "id": "test-device",
            "timeout": 2,
            "alert_email": "test@example.com"
        })
    assert response.status_code == 201
    assert response.json()["id"] == "test-device"
    assert response.json()["status"] == "ACTIVE"
    assert "test-device" in monitors

@pytest.mark.asyncio
async def test_duplicate_monitor():
    payload = {
        "id": "dup-device",
        "timeout": 2,
        "alert_email": "test@example.com"
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/monitors", json=payload)
        response = await ac.post("/monitors", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "Monitor already exists"

@pytest.mark.asyncio
async def test_heartbeat_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/monitors/unknown/heartbeat")
    assert response.status_code == 404
    assert response.json()["detail"] == "Monitor not found"

@pytest.mark.asyncio
async def test_alert_trigger():
    # Register monitor with 1s timeout
    timeout = 1
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/monitors", json={
            "id": "alert-device",
            "timeout": timeout,
            "alert_email": "test@example.com"
        })
    
    # Wait for timeout + grace + a little buffer
    await asyncio.sleep(timeout + GRACE_PERIOD + 0.5)
    
    assert monitors["alert-device"]["status"] == "DOWN"

@pytest.mark.asyncio
async def test_heartbeat_reset():
    timeout = 2
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/monitors", json={
            "id": "reset-device",
            "timeout": timeout,
            "alert_email": "test@example.com"
        })
        
        # Wait for some time but less than timeout + grace
        await asyncio.sleep(1)
        
        # Send heartbeat
        response = await ac.post("/monitors/reset-device/heartbeat")
        assert response.status_code == 200
    
    # Wait again (the original timer would have expired by now if not reset)
    await asyncio.sleep(timeout + GRACE_PERIOD - 0.5)
    
    # Status should still be ACTIVE
    assert monitors["reset-device"]["status"] == "ACTIVE"

@pytest.mark.asyncio
async def test_pause_feature():
    timeout = 1
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/monitors", json={
            "id": "pause-device",
            "timeout": timeout,
            "alert_email": "test@example.com"
        })
        
        # Pause
        response = await ac.post("/monitors/pause-device/pause")
        assert response.status_code == 200
    
    assert monitors["pause-device"]["status"] == "PAUSED"
    
    # Wait beyond timeout + grace
    await asyncio.sleep(timeout + GRACE_PERIOD + 0.5)
    
    # Should still be PAUSED, not DOWN
    assert monitors["pause-device"]["status"] == "PAUSED"

@pytest.mark.asyncio
async def test_resume_via_heartbeat():
    timeout = 1
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/monitors", json={
            "id": "resume-device",
            "timeout": timeout,
            "alert_email": "test@example.com"
        })
        
        # Pause
        await ac.post("/monitors/resume-device/pause")
        assert monitors["resume-device"]["status"] == "PAUSED"
        
        # Resume via heartbeat
        response = await ac.post("/monitors/resume-device/heartbeat")
        assert response.status_code == 200
        assert monitors["resume-device"]["status"] == "ACTIVE"
    
    # Verify it can still go DOWN after resume
    await asyncio.sleep(timeout + GRACE_PERIOD + 0.5)
    assert monitors["resume-device"]["status"] == "DOWN"
