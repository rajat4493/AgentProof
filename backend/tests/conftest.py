import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_PORT = 8901
os.environ.setdefault("SIMULATOR_BASE_URL", f"http://127.0.0.1:{TEST_PORT}")
os.environ.setdefault("AGENT_WRITE_CREDENTIAL", "agent-write-demo-credential")
os.environ.setdefault("VERIFIER_READ_CREDENTIAL", "verifier-read-demo-credential")

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Customer, Order


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(scope="session", autouse=True)
def _live_server():
    """app.agent.run_agent makes real HTTP calls (real network boundary,
    same as the agent's write credential hitting the deployed simulator) —
    so the test suite runs a real server rather than an in-process ASGI
    transport."""

    config = uvicorn.Config(app, host="127.0.0.1", port=TEST_PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    for _ in range(100):
        try:
            httpx.get(f"http://127.0.0.1:{TEST_PORT}/api/health", timeout=0.5)
            break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        raise RuntimeError("test server did not start in time")

    yield

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(autouse=True)
def _clean_db():
    db = SessionLocal()
    try:
        db.execute(text("DELETE FROM runs"))
        db.execute(text("DELETE FROM tasks"))
        db.execute(text("DELETE FROM messages"))
        db.execute(text("DELETE FROM refunds"))
        db.execute(text("DELETE FROM orders"))
        db.execute(text("DELETE FROM customers"))
        db.commit()
        db.add(Customer(id="C-891", name="Jordan Rivera", email="jordan.rivera@example.com"))
        db.add(Order(id="ORD-1047", customer_id="C-891", amount_minor_units=18500, currency="EUR"))
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture()
def client():
    return TestClient(app)
