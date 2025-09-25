"""
자세 인식 통합 서버 메인 실행 파일
WebSocket 서버와 REST API 서버를 동시에 실행
"""

import asyncio
import signal
import sys
import threading
import logging
import uvicorn
import psutil
from websocket_server import start_websocket_server
from starlette.middleware.base import BaseHTTPMiddleware
from statistics_api import app as fastapi_app
from logger_config import setup_logging, log_server_start, log_server_shutdown, log_system_health
from config import config

# 로깅 설정
setup_logging(log_level=config.get_log_level_int())
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """시그널 핸들러 (Ctrl+C 등)"""
    logger.info(f"시그널 {signum} 수신, 서버를 종료합니다...")
    log_server_shutdown()
    sys.exit(0)

def run_fastapi_server():
    """FastAPI 서버 실행 (별도 스레드)"""
    try:
        uvicorn.run(
            fastapi_app,
            host=config.SERVER_HOST,
            port=config.API_PORT,
            log_level="info",
            access_log=False  # 너무 많은 로그 방지
        )
    except Exception as e:
        logger.error(f"FastAPI 서버 오류: {e}")

async def system_monitor():
    """시스템 상태 모니터링 (주기적 실행)"""
    while True:
        try:
            # 시스템 리소스 정보 수집
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            memory_percent = memory_info.percent
            
            # 활성 연결 수 (WebSocket 서버에서 가져오기)
            # 여기서는 간단히 0으로 설정 (실제로는 WebSocket 서버에서 가져와야 함)
            active_connections = 0
            
            # 시스템 상태 로그
            log_system_health(cpu_percent, memory_percent, active_connections)
            
            # 30초마다 체크
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"시스템 모니터링 오류: {e}")
            await asyncio.sleep(30)

async def main():
    """메인 함수"""
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=== 자세 인식 통합 서버 시작 ===")
    logger.info(f"WebSocket 서버: ws://{config.SERVER_HOST}:{config.WEBSOCKET_PORT}")
    logger.info(f"REST API 서버: http://{config.SERVER_HOST}:{config.API_PORT}")
    logger.info(f"API 문서: http://{config.SERVER_HOST}:{config.API_PORT}/docs")
    logger.info("Ctrl+C를 눌러 서버를 종료할 수 있습니다.")
    logger.info("=====================================")
    
    try:
        # FastAPI 서버를 별도 스레드에서 실행
        fastapi_thread = threading.Thread(
            target=run_fastapi_server, 
            daemon=True,
            name="FastAPI-Server"
        )
        fastapi_thread.start()
        logger.info("FastAPI 서버 스레드 시작됨")
        
        # 시스템 모니터링 태스크 시작
        monitor_task = asyncio.create_task(system_monitor())
        logger.info("시스템 모니터링 시작됨")
        
        # WebSocket 서버를 메인 스레드에서 실행
        logger.info("WebSocket 서버 시작 중...")
        await start_websocket_server()
        
    except KeyboardInterrupt:
        logger.info("사용자에 의해 서버가 종료되었습니다")
    except Exception as e:
        logger.error(f"서버 실행 중 오류 발생: {e}")
        raise
    finally:
        log_server_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass