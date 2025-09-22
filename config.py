"""
환경 변수 설정 모듈
.env 파일에서 환경 변수를 로드하고 기본값을 제공합니다.
"""

import os
from pathlib import Path
from typing import Any, Union
import logging

# 로거 설정
logger = logging.getLogger(__name__)

class Config:
    """환경 설정 클래스"""
    
    def __init__(self):
        self.load_env_file()
        
    def load_env_file(self):
        """환경 변수 파일 로드"""
        env_path = Path('.env')
        if env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()
                logger.info(f"환경 변수 파일 로드 완료: {env_path}")
            except Exception as e:
                logger.warning(f"환경 변수 파일 로드 실패: {e}")
        else:
            logger.info("환경 변수 파일(.env)이 없습니다. 기본값을 사용합니다.")
    
    def get_env(self, key: str, default: Any = None, cast_type: type = str) -> Any:
        """환경 변수 값 가져오기 (타입 변환 지원)"""
        value = os.getenv(key, default)
        
        if value is None:
            return default
            
        if cast_type == bool:
            return str(value).lower() in ('true', '1', 'yes', 'on')
        elif cast_type == int:
            try:
                return int(value)
            except ValueError:
                logger.warning(f"환경 변수 {key}의 값 '{value}'를 int로 변환할 수 없습니다. 기본값 {default} 사용")
                return default
        elif cast_type == float:
            try:
                return float(value)
            except ValueError:
                logger.warning(f"환경 변수 {key}의 값 '{value}'를 float로 변환할 수 없습니다. 기본값 {default} 사용")
                return default
        else:
            return str(value)
    
    # 서버 설정
    @property
    def SERVER_HOST(self) -> str:
        return self.get_env('SERVER_HOST', '0.0.0.0')
    
    @property
    def SERVER_PORT(self) -> int:
        return self.get_env('SERVER_PORT', 8765, int)
    
    @property
    def WEBSOCKET_PORT(self) -> int:
        return self.get_env('WEBSOCKET_PORT', 8765, int)
    
    @property
    def API_PORT(self) -> int:
        return self.get_env('API_PORT', 8766, int)
    
    @property
    def SERVER_PING_INTERVAL(self) -> int:
        return self.get_env('SERVER_PING_INTERVAL', 30, int)
    
    @property
    def SERVER_PING_TIMEOUT(self) -> int:
        return self.get_env('SERVER_PING_TIMEOUT', 10, int)
    
    # 데이터베이스 설정
    @property
    def DATABASE_PATH(self) -> str:
        return self.get_env('DATABASE_PATH', 'posture_data.db')
    
    @property
    def DATABASE_BACKUP_ENABLED(self) -> bool:
        return self.get_env('DATABASE_BACKUP_ENABLED', True, bool)
    
    @property
    def DATABASE_BACKUP_INTERVAL(self) -> int:
        return self.get_env('DATABASE_BACKUP_INTERVAL', 3600, int)
    
    # 머신러닝 모델 설정
    @property
    def MODEL_PATH(self) -> str:
        return self.get_env('MODEL_PATH', 'model_lr.joblib')
    
    @property
    def MODEL_CONFIDENCE_THRESHOLD(self) -> float:
        return self.get_env('MODEL_CONFIDENCE_THRESHOLD', 0.1, float)
    
    @property
    def MODEL_FALLBACK_ENABLED(self) -> bool:
        return self.get_env('MODEL_FALLBACK_ENABLED', True, bool)
    
    # 로깅 설정
    @property
    def LOG_LEVEL(self) -> str:
        return self.get_env('LOG_LEVEL', 'INFO').upper()
    
    @property
    def LOG_FILE(self) -> str:
        return self.get_env('LOG_FILE', 'posture_server.log')
    
    @property
    def LOG_MAX_SIZE(self) -> int:
        return self.get_env('LOG_MAX_SIZE', 10485760, int)  # 10MB
    
    @property
    def LOG_BACKUP_COUNT(self) -> int:
        return self.get_env('LOG_BACKUP_COUNT', 5, int)
    
    @property
    def LOG_CONSOLE_ENABLED(self) -> bool:
        return self.get_env('LOG_CONSOLE_ENABLED', True, bool)
    
    # 성능 모니터링 설정
    @property
    def PERFORMANCE_STATS_INTERVAL(self) -> int:
        return self.get_env('PERFORMANCE_STATS_INTERVAL', 60, int)
    
    @property
    def MAX_CLIENTS(self) -> int:
        return self.get_env('MAX_CLIENTS', 100, int)
    
    @property
    def MAX_RESPONSE_TIME_MS(self) -> int:
        return self.get_env('MAX_RESPONSE_TIME_MS', 5000, int)
    
    # FSR 센서 설정
    @property
    def FSR_SENSOR_COUNT(self) -> int:
        return self.get_env('FSR_SENSOR_COUNT', 11, int)
    
    @property
    def FSR_VALUE_MIN(self) -> int:
        return self.get_env('FSR_VALUE_MIN', 0, int)
    
    @property
    def FSR_VALUE_MAX(self) -> int:
        return self.get_env('FSR_VALUE_MAX', 1024, int)
    
    @property
    def FSR_VALIDATION_ENABLED(self) -> bool:
        return self.get_env('FSR_VALIDATION_ENABLED', True, bool)
    
    # 보안 설정
    @property
    def ENABLE_CLIENT_AUTH(self) -> bool:
        return self.get_env('ENABLE_CLIENT_AUTH', False, bool)
    
    @property
    def CLIENT_AUTH_TOKEN(self) -> str:
        return self.get_env('CLIENT_AUTH_TOKEN', '')
    
    @property
    def CORS_ENABLED(self) -> bool:
        return self.get_env('CORS_ENABLED', True, bool)
    
    @property
    def CORS_ORIGINS(self) -> str:
        return self.get_env('CORS_ORIGINS', '*')
    
    # 개발/디버그 설정
    @property
    def DEBUG_MODE(self) -> bool:
        return self.get_env('DEBUG_MODE', False, bool)
    
    @property
    def TEST_MODE(self) -> bool:
        return self.get_env('TEST_MODE', False, bool)
    
    @property
    def DUMMY_MODEL_ENABLED(self) -> bool:
        return self.get_env('DUMMY_MODEL_ENABLED', False, bool)
    
    # 데이터 저장 설정
    @property
    def SAVE_RAW_DATA(self) -> bool:
        return self.get_env('SAVE_RAW_DATA', True, bool)
    
    @property
    def SAVE_PREDICTIONS(self) -> bool:
        return self.get_env('SAVE_PREDICTIONS', True, bool)
    
    @property
    def DATA_RETENTION_DAYS(self) -> int:
        return self.get_env('DATA_RETENTION_DAYS', 30, int)
    
    def get_log_level_int(self) -> int:
        """로그 레벨을 정수로 변환"""
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return levels.get(self.LOG_LEVEL, logging.INFO)
    
    def validate_config(self) -> bool:
        """설정값 유효성 검사"""
        errors = []
        
        # 포트 범위 검사
        if not (1 <= self.SERVER_PORT <= 65535):
            errors.append(f"SERVER_PORT는 1-65535 범위여야 합니다: {self.SERVER_PORT}")
        
        if not (1 <= self.WEBSOCKET_PORT <= 65535):
            errors.append(f"WEBSOCKET_PORT는 1-65535 범위여야 합니다: {self.WEBSOCKET_PORT}")
        
        if not (1 <= self.API_PORT <= 65535):
            errors.append(f"API_PORT는 1-65535 범위여야 합니다: {self.API_PORT}")
        
        if self.WEBSOCKET_PORT == self.API_PORT:
            errors.append(f"WEBSOCKET_PORT와 API_PORT는 달라야 합니다: {self.WEBSOCKET_PORT}")
        
        # FSR 센서 개수 검사
        if self.FSR_SENSOR_COUNT <= 0:
            errors.append(f"FSR_SENSOR_COUNT는 양수여야 합니다: {self.FSR_SENSOR_COUNT}")
        
        # 데이터 보존 기간 검사
        if self.DATA_RETENTION_DAYS <= 0:
            errors.append(f"DATA_RETENTION_DAYS는 양수여야 합니다: {self.DATA_RETENTION_DAYS}")
        
        # 로그 파일 크기 검사
        if self.LOG_MAX_SIZE <= 0:
            errors.append(f"LOG_MAX_SIZE는 양수여야 합니다: {self.LOG_MAX_SIZE}")
        
        if errors:
            for error in errors:
                logger.error(f"설정 오류: {error}")
            return False
        
        logger.info("모든 설정값이 유효합니다")
        return True
    
    def print_config(self):
        """현재 설정값 출력 (디버그용)"""
        logger.info("=== 현재 환경 설정 ===")
        logger.info(f"WebSocket 서버: {self.SERVER_HOST}:{self.WEBSOCKET_PORT}")
        logger.info(f"REST API 서버: {self.SERVER_HOST}:{self.API_PORT}")
        logger.info(f"데이터베이스: {self.DATABASE_PATH}")
        logger.info(f"모델: {self.MODEL_PATH}")
        logger.info(f"로그 레벨: {self.LOG_LEVEL}")
        logger.info(f"FSR 센서 개수: {self.FSR_SENSOR_COUNT}")
        logger.info(f"디버그 모드: {self.DEBUG_MODE}")
        logger.info("=====================")

# 전역 설정 인스턴스
config = Config()