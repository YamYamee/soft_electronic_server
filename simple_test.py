"""
자세 인식 서버 간단 테스트 스크립트
"""

import asyncio
import websockets
import json
import logging

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_server():
    """서버 기능 간단 테스트"""
    try:
        # 서버에 연결
        uri = "ws://localhost:8765"
        logger.info(f"서버 연결 시도: {uri}")
        
        async with websockets.connect(uri) as websocket:
            logger.info("서버 연결 성공!")
            
            # 테스트 데이터 생성 (정자세)
            test_message = {
                "id": 1,
                "device_id": "test_device_001",
                "IMU": {
                    "accel": [0.1, 0.2, 9.8],
                    "gyro": [0.01, 0.02, 0.03]
                },
                "FSR": [489, 625, 581, 483, 375, 517, 571, 530, 372, 398, 248]
            }
            
            # 메시지 전송
            await websocket.send(json.dumps(test_message))
            logger.info(f"테스트 데이터 전송: {test_message}")
            
            # 응답 대기
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            response_data = json.loads(response)
            
            logger.info(f"서버 응답 수신:")
            logger.info(f"  - 메시지 ID: {response_data.get('id')}")
            logger.info(f"  - 예측 자세: {response_data.get('posture')}")
            logger.info(f"  - 신뢰도: {response_data.get('confidence')}")
            
            if 'error' in response_data:
                logger.error(f"서버 에러: {response_data['error']}")
            else:
                logger.info("✅ 테스트 성공!")
                
            # 추가 테스트 - 다른 자세 패턴
            test_patterns = [
                {"name": "오른쪽 치우침", "fsr": [200, 300, 400, 500, 600, 100, 150, 200, 100, 150, 100]},
                {"name": "왼쪽 치우침", "fsr": [600, 500, 400, 300, 200, 400, 350, 300, 250, 200, 150]},
                {"name": "앞쪽 치우침", "fsr": [800, 700, 600, 200, 100, 800, 700, 300, 200, 100, 50]}
            ]
            
            for i, pattern in enumerate(test_patterns, 2):
                test_msg = {
                    "id": i,
                    "device_id": "test_device_001",
                    "FSR": pattern["fsr"]
                }
                
                await websocket.send(json.dumps(test_msg))
                logger.info(f"추가 테스트 전송 - {pattern['name']}")
                
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                logger.info(f"  응답: 자세 {response_data.get('posture')}, 신뢰도 {response_data.get('confidence')}")
                
                await asyncio.sleep(1)
            
            logger.info("🎉 모든 테스트 완료!")
                
    except websockets.exceptions.ConnectionRefused:
        logger.error("❌ 서버 연결 실패! 서버가 실행 중인지 확인하세요.")
        logger.info("서버 실행 명령: python main.py")
    except asyncio.TimeoutError:
        logger.error("❌ 서버 응답 시간 초과")
    except Exception as e:
        logger.error(f"❌ 테스트 실행 중 오류: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("자세 인식 WebSocket 서버 테스트")
    print("=" * 50)
    
    try:
        asyncio.run(test_server())
    except KeyboardInterrupt:
        print("\n테스트가 중단되었습니다.")