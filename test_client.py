"""
자세 인식 WebSocket 서버 테스트 클라이언트
실제 FSR 데이터를 사용하여 서버 기능을 테스트합니다.
"""

import asyncio
import websockets
import json
import random
import time
import logging

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestClient:
    def __init__(self, server_uri="ws://localhost:8765"):
        self.server_uri = server_uri
        self.message_id = 0
        
    def generate_test_fsr_data(self, posture_type=0):
        """테스트용 FSR 데이터 생성"""
        # 각 자세별 대표적인 FSR 패턴 (실제 데이터 기반)
        fsr_patterns = {
            0: [489, 625, 581, 483, 375, 517, 571, 530, 372, 398, 248],  # 정자세
            1: [435, 718, 521, 533, 491, 597, 503, 484, 367, 617, 332],  # 오른쪽 다리꼬기
            2: [435, 718, 521, 533, 491, 597, 503, 484, 367, 617, 332],  # 왼쪽 다리꼬기 (임시)
            3: [527, 643, 0, 0, 0, 0, 454, 576, 0, 712, 430],           # 등 기대고 엉덩이 앞으로
            4: [517, 680, 688, 500, 398, 493, 397, 371, 276, 224, 144], # 거북목
            5: [222, 156, 24, 0, 390, 672, 687, 495, 266, 675, 250],    # 오른쪽 팔걸이
            6: [0, 672, 485, 279, 312, 518, 767, 613, 170, 478, 339],   # 왼쪽 팔걸이
            7: [545, 703, 439, 410, 369, 553, 703, 123, 365, 227, 552]  # 목 앞으로
        }
        
        base_pattern = fsr_patterns.get(posture_type, fsr_patterns[0])
        
        # 약간의 노이즈 추가 (실제 센서 데이터처럼)
        noisy_data = []
        for value in base_pattern:
            noise = random.randint(-10, 10)
            noisy_value = max(0, value + noise)  # 음수 방지
            noisy_data.append(noisy_value)
        
        return noisy_data
    
    def create_test_message(self, posture_type=0):
        """테스트 메시지 생성"""
        self.message_id += 1
        
        message = {
            "id": self.message_id,
            "device_id": f"test_device_{random.randint(1000, 9999)}",
            "IMU": {
                "accel": [random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(9, 10)],
                "gyro": [random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1)]
            },
            "FSR": self.generate_test_fsr_data(posture_type)
        }
        
        return message
    
    async def send_test_data(self, websocket, posture_type=0, count=1):
        """테스트 데이터 전송"""
        for i in range(count):
            message = self.create_test_message(posture_type)
            
            # 메시지 전송
            await websocket.send(json.dumps(message))
            logger.info(f"테스트 데이터 전송 - 메시지 ID: {message['id']}, 자세 타입: {posture_type}")
            
            # 응답 대기
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                logger.info(f"서버 응답 - ID: {response_data.get('id')}, "
                           f"예측 자세: {response_data.get('posture')}, "
                           f"신뢰도: {response_data.get('confidence')}")
                
                if 'error' in response_data:
                    logger.error(f"서버 에러: {response_data['error']}")
                
            except asyncio.TimeoutError:
                logger.error("서버 응답 대기 시간 초과")
            except Exception as e:
                logger.error(f"응답 처리 오류: {e}")
            
            if count > 1:
                await asyncio.sleep(1)  # 다음 메시지 전송 전 대기
    
    async def run_interactive_test(self):
        """대화형 테스트 실행"""
        try:
            async with websockets.connect(self.server_uri) as websocket:
                logger.info(f"서버에 연결됨: {self.server_uri}")
                
                while True:
                    print("\n=== 자세 인식 서버 테스트 클라이언트 ===")
                    print("0: 정자세")
                    print("1: 오른쪽 다리꼬기")
                    print("2: 왼쪽 다리꼬기")
                    print("3: 등 기대고 엉덩이 앞으로")
                    print("4: 거북목(폰 보면서 목 숙이기)")
                    print("5: 오른쪽 팔걸이")
                    print("6: 왼쪽 팔걸이")
                    print("7: 목 앞으로 나오는(컴퓨터 할 때)")
                    print("8: 자동 테스트 (모든 자세)")
                    print("9: 종료")
                    
                    choice = input("테스트할 자세를 선택하세요 (0-9): ").strip()
                    
                    if choice == '9':
                        break
                    elif choice == '8':
                        # 자동 테스트
                        logger.info("자동 테스트 시작 - 모든 자세 테스트")
                        for posture in range(8):
                            logger.info(f"자세 {posture} 테스트 중...")
                            await self.send_test_data(websocket, posture, 1)
                            await asyncio.sleep(2)
                        logger.info("자동 테스트 완료")
                    elif choice.isdigit() and 0 <= int(choice) <= 7:
                        posture_type = int(choice)
                        count = input("전송할 메시지 수 (기본값: 1): ").strip()
                        count = int(count) if count.isdigit() else 1
                        
                        await self.send_test_data(websocket, posture_type, count)
                    else:
                        print("잘못된 선택입니다.")
                
                logger.info("테스트 클라이언트 종료")
                
        except websockets.exceptions.ConnectionRefused:
            logger.error("서버 연결 실패. 서버가 실행 중인지 확인하세요.")
        except KeyboardInterrupt:
            logger.info("사용자에 의해 테스트가 중단되었습니다.")
        except Exception as e:
            logger.error(f"테스트 클라이언트 오류: {e}")
    
    async def run_stress_test(self, duration_seconds=60, messages_per_second=5):
        """스트레스 테스트 실행"""
        logger.info(f"스트레스 테스트 시작 - 지속시간: {duration_seconds}초, 초당 메시지: {messages_per_second}")
        
        try:
            async with websockets.connect(self.server_uri) as websocket:
                start_time = time.time()
                message_count = 0
                
                while time.time() - start_time < duration_seconds:
                    # 랜덤한 자세 타입 선택
                    posture_type = random.randint(0, 7)
                    
                    # 메시지 전송
                    message = self.create_test_message(posture_type)
                    await websocket.send(json.dumps(message))
                    message_count += 1
                    
                    # 응답 수신 (논블로킹)
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                        response_data = json.loads(response)
                        if message_count % 10 == 0:  # 10개마다 로그
                            logger.info(f"메시지 {message_count}: 자세 {response_data.get('posture')}, "
                                      f"신뢰도 {response_data.get('confidence')}")
                    except asyncio.TimeoutError:
                        pass
                    
                    # 속도 조절
                    await asyncio.sleep(1.0 / messages_per_second)
                
                elapsed_time = time.time() - start_time
                logger.info(f"스트레스 테스트 완료 - 총 메시지: {message_count}, "
                           f"실제 속도: {message_count/elapsed_time:.1f} msg/sec")
                
        except Exception as e:
            logger.error(f"스트레스 테스트 오류: {e}")

async def main():
    """메인 함수"""
    import sys
    
    client = TestClient()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'stress':
        # 스트레스 테스트 모드
        await client.run_stress_test()
    else:
        # 대화형 테스트 모드
        await client.run_interactive_test()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass