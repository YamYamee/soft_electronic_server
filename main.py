"""
자세 인식 WebSocket 서버 메인 실행 파일
"""

import asyncio
import signal
import sys
import logging
from websocket_server import PostureWebSocketServer
from logger_config import setup_logging, log_server_start, log_server_shutdown

# 로깅 설정
setup_logging(log_level=logging.INFO)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """시그널 핸들러 (Ctrl+C 등)"""
    logger.info(f"시그널 {signum} 수신, 서버를 종료합니다...")
    log_server_shutdown()
    sys.exit(0)

async def main():
    """메인 함수"""
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 서버 설정
    host = "0.0.0.0"  # 모든 인터페이스에서 접속 허용
    port = 8765
    
    logger.info("자세 인식 WebSocket 서버를 시작합니다...")
    logger.info(f"서버 주소: ws://{host}:{port}")
    logger.info("Ctrl+C를 눌러 서버를 종료할 수 있습니다.")
    
    try:
        # 서버 인스턴스 생성 및 시작
        server = PostureWebSocketServer(host=host, port=port)
        await server.start_server()
        
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