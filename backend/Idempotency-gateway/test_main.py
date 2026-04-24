import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app, idempotency_store, locks

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_store():
    # Clear memory between tests to ensure isolation
    idempotency_store.clear()
    locks.clear()

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "API running"}

def test_missing_idempotency_key_header():
    response = client.post("/process-payment", json={"amount": 100, "currency": "GHS"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing Idempotency-Key"

def test_successful_payment_processing():
    # Note: TestClient does not simulate the 2s delay in a way that blocks other tests
    # unless we use an async client, but for basic logic it works.
    headers = {"Idempotency-Key": "test-key-1"}
    payload = {"amount": 100, "currency": "GHS"}
    response = client.post("/process-payment", headers=headers, json=payload)
    
    assert response.status_code == 200
    assert response.json() == {"message": "Charged 100.0 GHS"}
    assert "X-Cache-Hit" not in response.headers

def test_idempotent_caching_returns_stored_response():
    headers = {"Idempotency-Key": "test-key-2"}
    payload = {"amount": 100, "currency": "GHS"}
    
    # First request
    client.post("/process-payment", headers=headers, json=payload)
    
    # Second request (identical)
    response = client.post("/process-payment", headers=headers, json=payload)
    
    assert response.status_code == 200
    assert response.json() == {"message": "Charged 100.0 GHS"}
    assert response.headers["X-Cache-Hit"] == "true"

def test_conflict_detection_different_body():
    headers = {"Idempotency-Key": "test-key-3"}
    
    # First request
    client.post("/process-payment", headers=headers, json={"amount": 100, "currency": "GHS"})
    
    # Second request with different body
    response = client.post("/process-payment", headers=headers, json={"amount": 200, "currency": "GHS"})
    
    assert response.status_code == 409
    assert response.json()["detail"] == "Idempotency key already used for a different request body."

def test_payment_status_endpoint():
    key = "status-key"
    payload = {"amount": 150, "currency": "USD"}
    
    # 404 for non-existent
    response = client.get(f"/payment-status/{key}")
    assert response.status_code == 404
    
    # Process payment
    client.post("/process-payment", headers={"Idempotency-Key": key}, json=payload)
    
    # 200 for completed
    response = client.get(f"/payment-status/{key}")
    assert response.status_code == 200
    assert response.json() == {"message": "Charged 150.0 USD"}

@pytest.mark.asyncio
async def test_concurrent_requests_handling():
    from httpx import AsyncClient, ASGITransport
    
    key = "concurrent-key"
    payload = {"amount": 100, "currency": "GHS"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Fire two requests concurrently
        tasks = [
            ac.post("/process-payment", headers={"Idempotency-Key": key}, json=payload),
            ac.post("/process-payment", headers={"Idempotency-Key": key}, json=payload)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify both succeeded
        assert results[0].status_code == 200
        assert results[1].status_code == 200
        
        # One should be a cache hit, one should not
        cache_hits = [r.headers.get("X-Cache-Hit") == "true" for r in results]
        assert any(cache_hits)
        assert not all(cache_hits)
