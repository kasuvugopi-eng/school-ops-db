# Trigger reload v56 - Enabled token query parameter on document download endpoint
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from app.api.router import api_router
from app.middleware.correlation_id import CorrelationIdMiddleware
from app.middleware.cors import setup_cors
from app.middleware.rate_limit import setup_rate_limit
from app.config import settings
from app.websocket.manager import ws_manager
from app.auth.jwt_handler import decode_token

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.database import async_sessionmaker_instance
from app.services.reminder_service import process_all_active_reminders

logger = logging.getLogger("uvicorn.error")

scheduler = AsyncIOScheduler()

async def run_reminders_job():
    try:
        async with async_sessionmaker_instance() as session:
            await process_all_active_reminders(session)
            await session.commit()
    except Exception as e:
        logger.exception(f"Failed to process scheduled reminders: {e}")

@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Auto-create missing database tables (e.g. announcements table)
    from app.database import engine, Base
    import app.models as _models  # Ensure models are imported without shadowing fastapi_app
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    scheduler.add_job(run_reminders_job, 'interval', minutes=15)
    scheduler.start()
    logger.info("Scheduler started with 15-minute reminder job.")
    
    # Start Telegram bot
    try:
        from app.telegram.bot import start_bot, stop_bot
        await start_bot(fastapi_app)
    except Exception as e:
        logger.warning(f"Telegram bot failed to start: {e}")
    yield
    # Stop Telegram bot
    try:
        from app.telegram.bot import stop_bot
        await stop_bot()
    except Exception:
        pass
    
    scheduler.shutdown()

app = FastAPI(title="School Operations Agent Platform", lifespan=lifespan)

app.add_middleware(CorrelationIdMiddleware)
setup_cors(app)
setup_rate_limit(app)

app.include_router(api_router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.websocket("/ws/school/{school_id}")
async def websocket_endpoint(websocket: WebSocket, school_id: str, token: str = None):
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.connect(websocket, school_id, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, school_id)
