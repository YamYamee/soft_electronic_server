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

def log_prediction_detailed(client_id, device_id, fsr_data, prediction_details, processing_time):
    """상세 예측 과정 로그"""
    logger = logging.getLogger(__name__)
    
    # 기본 정보
    logger.info("🔍 [예측 시작] " + "="*50)
    logger.info(f"📱 클라이언트: {client_id} | 디바이스: {device_id}")
    logger.info(f"📊 FSR 데이터: {fsr_data}")
    
    # 개별 모델 예측 결과
    if 'individual_predictions' in prediction_details:
        logger.info("🤖 개별 모델 예측 결과:")
        individual_preds = prediction_details['individual_predictions']
        individual_confs = prediction_details.get('individual_confidences', {})
        
        for model_name, prediction in individual_preds.items():
            confidence = individual_confs.get(model_name, 0.0)
            logger.info(f"  • {model_name.upper()}: 자세 {prediction} (신뢰도 {confidence:.3f})")
    
    # 투표 점수
    if 'voting_scores' in prediction_details:
        voting_scores = prediction_details['voting_scores']
        logger.info("🗳️  앙상블 투표 점수:")
        for i, score in enumerate(voting_scores):
            if score > 0:
                logger.info(f"  • 자세 {i}: {score:.3f}")
    
    # 최종 결과
    final_pred = prediction_details.get('ensemble_prediction', 0)
    final_conf = prediction_details.get('ensemble_confidence', 0.0)
    logger.info(f"✅ 최종 예측: 자세 {final_pred} (신뢰도 {final_conf:.3f})")
    logger.info(f"⏱️  처리 시간: {processing_time:.1f}ms")
    logger.info("🏁 [예측 완료] " + "="*50)

def log_model_loading():
    """모델 로딩 과정 로그"""
    logger = logging.getLogger(__name__)
    logger.info("🚀 앙상블 모델 시스템 초기화 중...")

def log_model_loaded(model_name, success=True):
    """개별 모델 로드 결과 로그"""
    logger = logging.getLogger(__name__)
    if success:
        logger.info(f"  ✅ {model_name.upper()} 모델 로드 성공")
    else:
        logger.warning(f"  ❌ {model_name.upper()} 모델 로드 실패")

def log_ensemble_summary(loaded_models, total_models):
    """앙상블 구성 완료 로그"""
    logger = logging.getLogger(__name__)
    logger.info(f"🎯 앙상블 구성 완료: {loaded_models}/{total_models} 모델 활성화")
    if loaded_models == 0:
        logger.warning("⚠️  ML 모델 없음 - 규칙 기반 모델로 대체")
    elif loaded_models < total_models:
        logger.warning(f"⚠️  일부 모델 누락 - {total_models - loaded_models}개 모델 로드 실패")

def log_data_preprocessing(original_data, processed_data, scaler_used=False):
    """데이터 전처리 과정 로그"""
    logger = logging.getLogger(__name__)
    logger.debug("🔧 데이터 전처리 수행:")
    logger.debug(f"  원본 데이터 형태: {original_data.shape if hasattr(original_data, 'shape') else len(original_data)}")
    logger.debug(f"  전처리 후 형태: {processed_data.shape}")
    logger.debug(f"  스케일러 사용: {'예' if scaler_used else '아니오'}")
    logger.debug(f"  전처리된 값 범위: [{processed_data.min():.3f}, {processed_data.max():.3f}]")

def log_db_save(table_name, success=True, error=None):
    """DB 저장 결과 로그"""
    logger = logging.getLogger(__name__)
    if success:
        logger.debug(f"💾 DB 저장 성공: {table_name} 테이블")  
    else:
        logger.error(f"💾 DB 저장 실패: {table_name} 테이블 - {error}")

def log_websocket_connection(client_id, action="connected"):
    """WebSocket 연결 상태 로그"""
    logger = logging.getLogger(__name__)
    if action == "connected":
        logger.info(f"🔌 클라이언트 연결: {client_id}")
    elif action == "disconnected":
        logger.info(f"🔌 클라이언트 연결 해제: {client_id}")
    elif action == "error":
        logger.error(f"🔌 클라이언트 연결 오류: {client_id}")

def log_api_request(endpoint, method="GET", client_ip=None):
    """API 요청 로그"""
    logger = logging.getLogger(__name__)
    client_info = f" ({client_ip})" if client_ip else ""
    logger.info(f"🌐 API 요청: {method} {endpoint}{client_info}")

def log_system_health(cpu_usage=None, memory_usage=None, active_connections=0):
    """시스템 상태 로그"""
    logger = logging.getLogger(__name__)
    health_info = f"💓 시스템 상태 - 활성 연결: {active_connections}"
    if cpu_usage:
        health_info += f", CPU: {cpu_usage:.1f}%"
    if memory_usage:
        health_info += f", 메모리: {memory_usage:.1f}%"
    logger.info(health_info)

def log_stage2_prediction_detailed(client_id, device_id, imu_data, stage1_result, prediction_details, processing_time):
    """2차 분류 상세 예측 과정 로그"""
    logger = logging.getLogger(__name__)
    
    # 헤더
    logger.info("=" * 50)
    logger.info(f"🎯 [2차 분류 시작] 클라이언트: {client_id}, 디바이스: {device_id}")
    logger.info(f"📊 1차 분류 결과: 자세 {stage1_result['prediction']} (신뢰도: {stage1_result['confidence']:.3f})")
    
    # IMU 데이터 로그
    if imu_data:
        logger.info("📱 IMU 센서 데이터:")
        if isinstance(imu_data, dict):
            logger.info(f"   • 가속도: X={imu_data.get('accel_x', 0):.3f}, Y={imu_data.get('accel_y', 0):.3f}, Z={imu_data.get('accel_z', 0):.3f}")
            logger.info(f"   • 자이로:  X={imu_data.get('gyro_x', 0):.3f}, Y={imu_data.get('gyro_y', 0):.3f}, Z={imu_data.get('gyro_z', 0):.3f}")
    
    # 개별 2차 모델 결과
    individual_preds = prediction_details.get('stage2_individual_predictions', {})
    individual_confs = prediction_details.get('stage2_individual_confidences', {})
    
    if individual_preds:
        logger.info("🤖 개별 2차 모델 예측 결과:")
        for model_name, prediction in individual_preds.items():
            confidence = individual_confs.get(model_name, 0.0)
            logger.info(f"   • {model_name.upper()}: 자세 {prediction} (신뢰도 {confidence:.3f})")
    
    # 투표 점수
    voting_scores = prediction_details.get('stage2_voting_scores', [])
    if voting_scores and any(score > 0 for score in voting_scores):
        logger.info("🗳️  2차 앙상블 투표 점수:")
        for i, score in enumerate(voting_scores):
            if score > 0.001:  # 의미있는 점수만 표시
                logger.info(f"   • 자세 {i}: {score:.3f}")
    
    # 최종 결과
    final_pred = prediction_details.get('stage2_final_prediction', 0)
    final_conf = prediction_details.get('stage2_final_confidence', 0.0)
    logger.info(f"✅ 2차 분류 최종 예측: 자세 {final_pred} (신뢰도 {final_conf:.3f})")
    logger.info(f"⏱️  2차 분류 처리 시간: {processing_time:.1f}ms")
    logger.info("🏁 [2차 분류 완료] " + "=" * 30)