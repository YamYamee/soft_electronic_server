# 자세 인식 WebSocket 서버

실시간으로 FSR(Force Sensitive Resistor) 센서 데이터를 받아 머신러닝 모델을 통해 사용자의 앉은 자세를 분석하는 WebSocket 서버입니다.

## 기능

- **WebSocket 서버**: 애플리케이션과 실시간 통신
- **자세 분류**: 8가지 앉은 자세 실시간 분석
- **머신러닝 모델**: 기 훈련된 모델을 사용한 빠른 예측
- **데이터베이스 저장**: SQLite를 사용한 예측 결과 저장
- **상세 로깅**: 서버 동작 및 성능 모니터링

## 지원 자세 분류

| ID  | 자세명                         | 설명                                      |
| --- | ------------------------------ | ----------------------------------------- |
| 0   | 정자세                         | 올바른 앉은 자세                          |
| 1   | 오른쪽 다리꼬기                | 오른쪽 다리를 왼쪽 다리 위에 올린 자세    |
| 2   | 왼쪽 다리꼬기                  | 왼쪽 다리를 오른쪽 다리 위에 올린 자세    |
| 3   | 등 기대고 엉덩이 앞으로        | 등받이에 기대고 엉덩이가 앞으로 나온 자세 |
| 4   | 거북목(폰 보면서 목 숙이기)    | 폰을 보면서 목을 아래로 숙인 자세         |
| 5   | 오른쪽 팔걸이                  | 오른쪽 팔걸이에 팔을 올린 자세            |
| 6   | 왼쪽 팔걸이                    | 왼쪽 팔걸이에 팔을 올린 자세              |
| 7   | 목 앞으로 나오는(컴퓨터 할 때) | 컴퓨터 작업 시 목이 앞으로 나온 자세      |

## 설치 및 실행

### 1. 요구사항

- Python 3.7 이상
- pip (Python 패키지 관리자)

### 2. 의존성 패키지 설치

#### Windows 환경:

```bash
# 패키지 자동 설치 (프로그램에서 자동 처리)
python main.py
```

#### Ubuntu/Linux 환경:

```bash
# 자동 설치 스크립트 사용 (권장)
chmod +x install_ubuntu.sh
./install_ubuntu.sh

# 수동 설치 - PEP 668 호환 방법들:

# 방법 1: 가상환경 사용 (가장 권장)
sudo apt update
sudo apt install python3 python3-pip python3-venv python3-dev python3-full
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 방법 2: 시스템 패키지 관리자 사용
sudo apt install python3-websockets python3-numpy python3-pandas python3-sklearn
# 추가 패키지는 사용자 로컬에 설치
python3 -m pip install --user joblib aiofiles typing-extensions

# 방법 3: --break-system-packages 옵션 (주의: 권장하지 않음)
python3 -m pip install -r requirements.txt --break-system-packages

# 서버 관리 스크립트 권한 부여
chmod +x server_manager.sh
```

**PEP 668 오류 해결:**
Ubuntu 22.04+에서 `error: externally-managed-environment` 오류가 발생하면 가상환경을 사용하세요:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

### 3. 환경 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하여 환경 변수를 설정할 수 있습니다:

```bash
# .env.example 파일을 복사하여 시작
cp .env.example .env
```

주요 환경 변수:

```bash
# 서버 설정
SERVER_HOST=3.34.159.75      # 서버 호스트 주소 (AWS EC2)
SERVER_PORT=8765             # 서버 포트 번호

# 데이터베이스 설정
DATABASE_PATH=posture_data.db # 데이터베이스 파일 경로

# 모델 설정
MODEL_PATH=model_lr.joblib   # 머신러닝 모델 파일 경로

# 로깅 설정
LOG_LEVEL=INFO               # 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
LOG_FILE=posture_server.log  # 로그 파일 이름
```

### 4. 서버 실행

#### Ubuntu 서버 빠른 시작:

```bash
# 1. 자동 설치 스크립트 실행
bash install_ubuntu.sh

# 2. 서버 시작
bash server_manager.sh start

# 3. 서버 상태 확인
bash server_manager.sh status

# 4. 로그 확인
bash server_manager.sh logs
```

#### Windows 환경:

```bash
# 메인 서버 실행
python main.py
```

#### Ubuntu/Linux 환경:

```bash
# 메인 서버 실행
python3 main.py

# 백그라운드 실행 (선택사항)
nohup python3 main.py > server.log 2>&1 &

# 프로세스 확인
ps aux | grep main.py
```

서버가 시작되면 환경 변수에서 설정한 주소(기본값: `ws://3.34.159.75:8765`)에서 WebSocket 연결을 받습니다.

## AWS EC2 배포 가이드

### 1. EC2 보안 그룹 설정

AWS 콘솔에서 EC2 인스턴스의 보안 그룹에 다음 규칙을 추가하세요:

```
유형: 사용자 지정 TCP
포트 범위: 8765
소스: 0.0.0.0/0 (모든 IP에서 접근) 또는 특정 IP 범위
설명: WebSocket Server Port
```

### 2. 서버 설정

```bash
# .env 파일 생성 및 설정
cp .env.example .env

# 서버 IP 확인 및 설정
curl http://checkip.amazonaws.com  # 현재 EC2 공용 IP 확인
echo "SERVER_HOST=3.34.159.75" > .env
echo "SERVER_PORT=8765" >> .env
```

### 3. 방화벽 설정 (Ubuntu)

```bash
# UFW 방화벽에서 포트 8765 열기
sudo ufw allow 8765
sudo ufw status  # 상태 확인
```

### 4. 외부 연결 테스트

```bash
# 서버에서 포트 리스닝 확인
sudo netstat -tlnp | grep :8765

# 다른 컴퓨터에서 연결 테스트
telnet 3.34.159.75 8765

# WebSocket 클라이언트 연결 주소
# ws://3.34.159.75:8765
```

### 5. 서버 자동 시작 설정 (systemd)

```bash
# 서비스 파일 생성
sudo nano /etc/systemd/system/posture-server.service

# 다음 내용 입력:
[Unit]
Description=Posture Recognition WebSocket Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/soft_electronic_server
Environment=PATH=/home/ubuntu/soft_electronic_server/venv/bin
ExecStart=/home/ubuntu/soft_electronic_server/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target

# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable posture-server
sudo systemctl start posture-server
sudo systemctl status posture-server
```

### 5. 테스트 클라이언트 실행

#### Windows 환경:

```bash
# 대화형 테스트 클라이언트
python test_client.py

# 스트레스 테스트
python test_client.py stress
```

#### Ubuntu/Linux 환경:

```bash
# 대화형 테스트 클라이언트
python3 test_client.py

# 스트레스 테스트
python3 test_client.py stress
```

## API 사용법

### 클라이언트 → 서버 (센서 데이터 전송)

```json
{
    "id": "메시지 고유 ID",
    "device_id": "디바이스 고유 ID",
    "IMU": "IMU 센서 데이터 (선택적)",
    "FSR": [센서1, 센서2, ..., 센서11]
}
```

**예시:**

```json
{
  "id": 1,
  "device_id": "device_001",
  "IMU": {
    "accel": [0.1, 0.2, 9.8],
    "gyro": [0.01, 0.02, 0.03]
  },
  "FSR": [489, 625, 581, 483, 375, 517, 571, 530, 372, 398, 248]
}
```

### 서버 → 클라이언트 (예측 결과 응답)

```json
{
  "id": "요청 메시지 ID",
  "posture": "예측된 자세 ID (0-7)",
  "confidence": "신뢰도 (0.0-1.0)"
}
```

**예시:**

```json
{
  "id": 1,
  "posture": 0,
  "confidence": 0.923
}
```

### 에러 응답

```json
{
  "id": "요청 메시지 ID",
  "error": "에러 메시지",
  "details": "상세 에러 정보"
}
```

## 프로젝트 구조

```
soft_electronic_server/
├── main.py                 # 메인 실행 파일
├── websocket_server.py     # WebSocket 서버 구현
├── model_predictor.py      # 머신러닝 모델 예측 모듈
├── database.py             # 데이터베이스 관리 모듈
├── logger_config.py        # 로깅 설정 모듈
├── config.py               # 환경 변수 설정 모듈
├── test_client.py          # 테스트 클라이언트
├── simple_test.py          # 간단한 기능 테스트
├── requirements.txt        # Python 의존성 패키지 목록
├── install_ubuntu.sh       # Ubuntu 자동 설치 스크립트
├── server_manager.sh       # 서버 관리 스크립트
├── .env                    # 환경 변수 설정 파일
├── .env.example            # 환경 변수 예시 파일
├── .gitignore              # Git 제외 파일 목록
├── README.md               # 상세 사용 설명서
├── model_lr.joblib         # 훈련된 머신러닝 모델
├── posture_data.db         # SQLite 데이터베이스 (자동 생성)
├── logs/                   # 로그 파일 디렉토리
│   └── posture_server.log
└── FSR/                    # 훈련 데이터 (참조용)
    └── *.csv
```

## 데이터베이스 스키마

### posture_predictions (예측 결과)

- `id`: 기본키
- `client_id`: 클라이언트 ID
- `device_id`: 디바이스 ID
- `timestamp`: 예측 시간
- `predicted_posture`: 예측된 자세 (0-7)
- `confidence`: 신뢰도
- `imu_data`: IMU 센서 데이터
- `fsr_data`: FSR 센서 데이터

### client_connections (클라이언트 연결 로그)

- `id`: 기본키
- `client_id`: 클라이언트 ID
- `device_id`: 디바이스 ID
- `connect_time`: 연결 시간
- `disconnect_time`: 연결 해제 시간
- `is_active`: 활성 상태

## 로깅

서버는 다음과 같은 로그를 생성합니다:

- **콘솔 출력**: 실시간 서버 상태 모니터링
- **파일 로깅**: `logs/posture_server.log`에 상세 로그 저장
- **로그 로테이션**: 10MB 단위로 자동 회전 (최대 5개 파일 유지)

## 성능 모니터링

서버는 다음 메트릭을 주기적으로 로깅합니다:

- 연결된 클라이언트 수
- 초당 예측 처리 수
- 평균 응답 시간
- 서버 가동 시간

## 주의사항

1. **FSR 데이터 형식**: 11개의 숫자 배열로 전송해야 합니다
2. **연결 안정성**: WebSocket 연결이 불안정한 경우 자동으로 재연결을 시도하세요
3. **데이터 유효성**: 음수 값이나 비정상적인 센서 값은 자동으로 필터링됩니다
4. **보안**: 프로덕션 환경에서는 적절한 인증 및 암호화를 추가하세요

## 문제 해결

### 서버가 시작되지 않는 경우

#### Windows 환경:

1. 포트 8765가 사용 중인지 확인
2. Python 환경 및 패키지 설치 상태 확인
3. `model_lr.joblib` 파일이 존재하는지 확인

#### Ubuntu/Linux 환경:

1. **의존성 패키지 설치**:
   ```bash
   pip3 install -r requirements.txt
   ```
2. **포트 사용 확인**:
   ```bash
   sudo netstat -tlnp | grep :8765
   # 또는
   sudo ss -tlnp | grep :8765
   ```
3. **방화벽 설정**:
   ```bash
   # Ubuntu UFW 방화벽 포트 열기
   sudo ufw allow 8765
   ```
4. **권한 문제**:
   ```bash
   # 실행 권한 확인
   chmod +x main.py
   ```

### 패키지 설치 오류 (Ubuntu)

```bash
# pip 업데이트
python3 -m pip install --upgrade pip

# 시스템 패키지 설치
sudo apt install python3-dev python3-setuptools

# 가상환경 사용 (권장)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 예측 정확도가 낮은 경우

1. FSR 센서 데이터가 올바른 형식인지 확인
2. 센서 배치가 훈련 데이터와 일치하는지 확인
3. 로그에서 데이터 유효성 검사 결과 확인

### 연결 문제 (AWS EC2)

#### 외부에서 서버에 연결할 수 없는 경우:

1. **EC2 보안 그룹 확인**:

   ```bash
   # AWS 콘솔에서 보안 그룹 규칙 확인
   # 포트 8765가 열려있는지 확인
   ```

2. **서버 IP 주소 확인**:

   ```bash
   # EC2 인스턴스의 공용 IP 확인
   curl http://checkip.amazonaws.com
   ```

3. **서버 실행 상태 확인**:

   ```bash
   # 서버가 정상적으로 실행 중인지 확인
   sudo netstat -tlnp | grep :8765
   ps aux | grep main.py
   ```

4. **방화벽 설정 확인**:

   ```bash
   # Ubuntu 방화벽 상태 확인
   sudo ufw status
   # 포트 8765가 허용되어 있는지 확인
   ```

5. **로그 확인**:

   ```bash
   # 서버 로그에서 오류 메시지 확인
   tail -f logs/posture_server.log
   ```

6. **클라이언트 연결 테스트**:
   ```javascript
   // JavaScript WebSocket 클라이언트 테스트
   const ws = new WebSocket("ws://3.34.159.75:8765");
   ws.onopen = () => console.log("연결 성공");
   ws.onerror = (err) => console.error("연결 실패:", err);
   ```

#### 일반적인 연결 문제:

1. 방화벽 설정 확인
2. 서버 주소와 포트 번호 확인 (ws://3.34.159.75:8765)
3. 네트워크 연결 상태 확인
4. SSL/TLS 설정 확인 (HTTPS 환경에서는 WSS 필요)

## 라이센스

이 프로젝트는 교육 및 연구 목적으로 제작되었습니다.

## 기여

버그 리포트나 기능 개선 제안은 이슈로 등록해 주세요.
