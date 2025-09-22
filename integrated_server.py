"""
통합 서버 - WebSocket과 REST API를 동시에 제공
"""

import asyncio
import threading
import uvicorn
from websocket_server import start_websocket_server
from statistics_api import app as fastapi_app
from config import config
import logging

# 로거 설정
logger = logging.getLogger(__name__)

def run_fastapi_server():
    """FastAPI 서버 실행 (별도 스레드)"""
    uvicorn.run(
        fastapi_app,
        host="0.0.0.0",
        port=config.API_PORT,
        log_level="info"
    )

def run_websocket_server():
    """WebSocket 서버 실행"""
    asyncio.run(start_websocket_server())

async def main():
    """메인 통합 서버"""
    logger.info("=== 자세 인식 통합 서버 시작 ===")
    logger.info(f"WebSocket 서버: ws://0.0.0.0:{config.WEBSOCKET_PORT}")
    logger.info(f"REST API 서버: http://0.0.0.0:{config.API_PORT}")
    logger.info("==============================")
    
    # FastAPI 서버를 별도 스레드에서 실행
    fastapi_thread = threading.Thread(target=run_fastapi_server, daemon=True)
    fastapi_thread.start()
    
    # WebSocket 서버를 메인 스레드에서 실행
    await start_websocket_server()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("서버가 종료되었습니다.")
    except Exception as e:
        logger.error(f"서버 실행 오류: {e}")