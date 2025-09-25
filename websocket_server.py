import asyncio
import websockets
import json
import uuid
import time
from typing import Dict, Set
import logging
from datetime import datetime

from model_predictor import predictor
from database import db
from config import config
from logger_config import (
    setup_logging, log_server_start, log_server_shutdown,
    log_client_data, log_prediction_result, log_error, log_performance_metrics
)

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)

class PostureWebSocketServer:
    def __init__(self, host=None, port=None):
        self.host = host or config.SERVER_HOST
        self.port = port or config.WEBSOCKET_PORT
        self.connected_clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.client_info: Dict[str, Dict] = {}
        self.performance_stats = {
            'total_predictions': 0,
            'start_time': time.time(),
            'response_times': []
        }
    
    async def register_client(self, websocket):
        """새 클라이언트 등록"""
        client_id = str(uuid.uuid4())
        self.connected_clients[client_id] = websocket
        
        # 클라이언트 정보 초기화
        self.client_info[client_id] = {
            'connect_time': datetime.now(),
            'predictions_count': 0,
            'last_activity': datetime.now()
        }
        
        # 데이터베이스에 연결 기록
        await db.log_client_connection(client_id)
        
        # 상세 연결 로그
        from logger_config import log_websocket_connection
        log_websocket_connection(client_id, "connected")
        logger.info(f"새 클라이언트 연결: {client_id} (총 {len(self.connected_clients)}명 연결)")
        
        return client_id
    
    async def unregister_client(self, client_id):
        """클라이언트 연결 해제"""
        if client_id in self.connected_clients:
            del self.connected_clients[client_id]
            
        if client_id in self.client_info:
            del self.client_info[client_id]
            
        # 데이터베이스에 연결 해제 기록
        await db.log_client_disconnection(client_id)
        
        # 상세 연결 해제 로그
        from logger_config import log_websocket_connection
        log_websocket_connection(client_id, "disconnected")
        logger.info(f"클라이언트 연결 해제: {client_id} (총 {len(self.connected_clients)}명 연결)")
    
    async def process_sensor_data(self, client_id, data):
        """센서 데이터 처리 및 자세 예측"""
        start_time = time.time()
        
        try:
            # 입력 데이터 검증
            required_fields = ['id', 'device_id', 'FSR']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"필수 필드 누락: {field}")
            
            # 데이터 추출
            message_id = data['id']
            device_id = data['device_id']
            imu_data = data.get('IMU')  # IMU 데이터는 받되 예측에는 사용 안함
            fsr_data = data['FSR']
            
            # FSR 데이터 유효성 검사
            if not predictor.validate_model_input(fsr_data):
                raise ValueError("유효하지 않은 FSR 데이터")
            
            log_client_data(client_id, "sensor", len(json.dumps(data)))
            
            # 자세 예측 수행 (클라이언트 정보 포함) - IMU는 예측에 사용하지 않음
            predicted_posture, confidence = predictor.predict_posture(
                fsr_data, imu_data, client_id=client_id, device_id=device_id
            )
            
            # 처리 시간 계산
            processing_time_ms = (time.time() - start_time) * 1000
            
            # 응답 데이터 생성 (NumPy 타입을 Python 기본 타입으로 변환)
            response_data = {
                "id": message_id,
                "posture": int(predicted_posture),  # numpy.int64 -> int 변환
                "confidence": float(round(confidence, 3))  # numpy.float64 -> float 변환
            }
            
            # 클라이언트에게 결과 전송
            await self.send_to_client(client_id, response_data)
            
            # 데이터베이스에 결과 저장
            await db.save_prediction(
                client_id=client_id,
                device_id=device_id,
                posture=predicted_posture,
                confidence=confidence,
                imu_data=imu_data,
                fsr_data=fsr_data
            )
            
            # 통계 업데이트
            self.update_performance_stats(processing_time_ms)
            self.client_info[client_id]['predictions_count'] += 1
            self.client_info[client_id]['last_activity'] = datetime.now()
            
            log_prediction_result(client_id, predicted_posture, confidence, processing_time_ms)
            
        except Exception as e:
            log_error("DATA_PROCESSING", str(e), client_id)
            
            # 에러 응답 전송
            error_response = {
                "id": data.get('id', 'unknown'),
                "error": "데이터 처리 중 오류가 발생했습니다",
                "details": str(e)
            }
            await self.send_to_client(client_id, error_response)
    
    async def send_to_client(self, client_id, data):
        """클라이언트에게 데이터 전송"""
        if client_id not in self.connected_clients:
            logger.warning(f"존재하지 않는 클라이언트 ID: {client_id}")
            return False
        
        try:
            websocket = self.connected_clients[client_id]
            message = json.dumps(data, ensure_ascii=False)
            await websocket.send(message)
            
            logger.debug(f"클라이언트 {client_id}에게 데이터 전송 완료")
            return True
            
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"클라이언트 {client_id} 연결이 이미 종료됨")
            await self.unregister_client(client_id)
            return False
        except Exception as e:
            log_error("SEND_ERROR", str(e), client_id)
            return False
    
    async def handle_client(self, websocket, path=None):
        """클라이언트 연결 처리"""
        client_id = await self.register_client(websocket)
        
        try:
            async for message in websocket:
                try:
                    # JSON 파싱
                    data = json.loads(message)
                    
                    # 센서 데이터 처리
                    await self.process_sensor_data(client_id, data)
                    
                except json.JSONDecodeError as e:
                    log_error("JSON_PARSE", f"잘못된 JSON 형식: {e}", client_id)
                    error_response = {
                        "error": "잘못된 JSON 형식",
                        "details": str(e)
                    }
                    await self.send_to_client(client_id, error_response)
                
                except Exception as e:
                    log_error("MESSAGE_HANDLING", str(e), client_id)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"클라이언트 {client_id} 연결 종료")
        except Exception as e:
            log_error("CLIENT_HANDLING", str(e), client_id)
        finally:
            await self.unregister_client(client_id)
    
    def update_performance_stats(self, response_time_ms):
        """성능 통계 업데이트"""
        self.performance_stats['total_predictions'] += 1
        self.performance_stats['response_times'].append(response_time_ms)
        
        # 최근 100개 응답시간만 유지
        if len(self.performance_stats['response_times']) > 100:
            self.performance_stats['response_times'] = self.performance_stats['response_times'][-100:]
    
    def get_performance_metrics(self):
        """성능 메트릭 계산"""
        stats = self.performance_stats
        elapsed_time = time.time() - stats['start_time']
        
        if elapsed_time > 0:
            predictions_per_second = stats['total_predictions'] / elapsed_time
        else:
            predictions_per_second = 0
        
        if stats['response_times']:
            avg_response_time = sum(stats['response_times']) / len(stats['response_times'])
        else:
            avg_response_time = 0
        
        return {
            'total_clients': len(self.connected_clients),
            'total_predictions': stats['total_predictions'],
            'predictions_per_second': predictions_per_second,
            'avg_response_time_ms': avg_response_time,
            'uptime_seconds': elapsed_time
        }
    
    async def log_periodic_stats(self):
        """주기적 통계 로깅"""
        while True:
            try:
                await asyncio.sleep(60)  # 1분마다
                metrics = self.get_performance_metrics()
                log_performance_metrics(
                    metrics['total_clients'],
                    metrics['predictions_per_second'],
                    metrics['avg_response_time_ms']
                )
            except Exception as e:
                logger.error(f"통계 로깅 오류: {e}")
    
    async def start_server(self):
        """서버 시작"""
        log_server_start()
        
        try:
            # 서버 설정 디버깅 정보
            logger.info(f"서버 바인딩 시도 - 호스트: {self.host}, 포트: {self.port}")
            
            # 통계 로깅 태스크 시작
            stats_task = asyncio.create_task(self.log_periodic_stats())
            
            # WebSocket 서버 시작
            server = await websockets.serve(
                self.handle_client, 
                self.host, 
                self.port,
                ping_interval=config.SERVER_PING_INTERVAL,
                ping_timeout=config.SERVER_PING_TIMEOUT
            )
            
            logger.info(f"WebSocket 서버 시작 성공 - 주소: ws://{self.host}:{self.port}")
            
            # 서버 실행 유지
            await server.wait_closed()
            
        except OSError as e:
            if "could not bind" in str(e):
                logger.error(f"포트 바인딩 실패: {e}")
                logger.error(f"포트 {self.port}가 이미 사용 중이거나 권한이 없습니다.")
                logger.info("해결 방법:")
                logger.info("1. 다른 포트 사용: SERVER_PORT=8766")
                logger.info("2. 기존 프로세스 종료: sudo lsof -ti:8765 | xargs sudo kill")
                logger.info("3. 권한 확인: sudo 없이 1024 이상 포트 사용")
            raise
        except Exception as e:
            log_error("SERVER_START", str(e))
            raise
        finally:
            log_server_shutdown()
# 서버 시작 함수
async def start_websocket_server():
    """WebSocket 서버 시작 (다른 모듈에서 호출용)"""
    server = PostureWebSocketServer()
    await server.start_server()

# 메인 실행 함수
async def main():
    from logger_config import log_server_start, log_server_shutdown
    log_server_start()
    try:
        await start_websocket_server()
    finally:
        log_server_shutdown()

if __name__ == "__main__":
    try:
        setup_logging()
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("사용자에 의해 서버가 종료되었습니다")
        from logger_config import log_server_shutdown
        log_server_shutdown()