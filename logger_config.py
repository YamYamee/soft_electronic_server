import logging
import logging.handlers
import os
from datetime import datetime
from config import config

def setup_logging(log_level=None, log_file=None):
    """로깅 시스템 설정"""
    
    # 환경 변수에서 설정값 가져오기
    if log_level is None:
        log_level = config.get_log_level_int()
    if log_file is None:
        log_file = config.LOG_FILE
    
    # 로그 디렉토리 생성
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file_path = os.path.join(log_dir, log_file)
    
    # 로그 포맷 설정
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 설정 (로테이션 지원)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path, 
        maxBytes=config.LOG_MAX_SIZE,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
    
    # WebSocket 라이브러리 로그 레벨 조정 (너무 상세한 로그 방지)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    
    logging.info("로깅 시스템 초기화 완료")
    logging.info(f"로그 레벨: {logging.getLevelName(log_level)}")
    logging.info(f"로그 파일: {log_file_path}")
    
    return root_logger

def log_server_start():
    """서버 시작 로그"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("자세 인식 WebSocket 서버 시작")
    logger.info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

def log_server_shutdown():
    """서버 종료 로그"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("자세 인식 WebSocket 서버 종료")
    logger.info(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

def log_client_data(client_id, data_type, data_size):
    """클라이언트 데이터 수신 로그"""
    logger = logging.getLogger(__name__)
    logger.debug(f"클라이언트 {client_id}로부터 {data_type} 데이터 수신 (크기: {data_size} bytes)")

def log_prediction_result(client_id, posture, confidence, processing_time_ms):
    """예측 결과 로그"""
    logger = logging.getLogger(__name__)
    logger.info(f"예측 완료 - 클라이언트: {client_id}, 자세: {posture}, 신뢰도: {confidence:.3f}, 처리시간: {processing_time_ms:.1f}ms")

def log_error(error_type, error_message, client_id=None):
    """에러 로그"""
    logger = logging.getLogger(__name__)
    if client_id:
        logger.error(f"[{error_type}] 클라이언트 {client_id}: {error_message}")
    else:
        logger.error(f"[{error_type}] {error_message}")

def log_performance_metrics(total_clients, predictions_per_second, avg_response_time_ms):
    """성능 메트릭 로그"""
    logger = logging.getLogger(__name__)
    logger.info(f"성능 메트릭 - 연결 클라이언트: {total_clients}, 초당 예측: {predictions_per_second:.1f}, 평균 응답시간: {avg_response_time_ms:.1f}ms")