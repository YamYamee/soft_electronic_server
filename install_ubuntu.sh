#!/bin/bash

# 자세 인식 WebSocket 서버 Ubuntu 설치 스크립트
# 사용법: bash install_ubuntu.sh

echo "========================================"
echo "자세 인식 WebSocket 서버 설치 시작"
echo "========================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 함수: 에러 체크
check_error() {
    if [ $? -ne 0 ]; then
        echo -e "${RED}오류: $1${NC}"
        exit 1
    fi
}

# 함수: 성공 메시지
success_msg() {
    echo -e "${GREEN}✓ $1${NC}"
}

# 함수: 정보 메시지
info_msg() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# 1. 시스템 업데이트
info_msg "시스템 패키지 업데이트 중..."
sudo apt update -y
check_error "시스템 업데이트 실패"
success_msg "시스템 업데이트 완료"

# 2. Python3 및 pip 설치
info_msg "Python3 및 관련 도구 설치 중..."
sudo apt install -y python3 python3-pip python3-venv python3-dev
check_error "Python3 설치 실패"
success_msg "Python3 설치 완료"

# 3. Python 버전 확인
python3_version=$(python3 --version)
info_msg "설치된 Python 버전: $python3_version"

# 4. pip 업그레이드
info_msg "pip 업그레이드 중..."
python3 -m pip install --upgrade pip
check_error "pip 업그레이드 실패"
success_msg "pip 업그레이드 완료"

# 5. 가상환경 생성 (선택사항)
read -p "가상환경을 생성하시겠습니까? (y/n): " create_venv
if [[ $create_venv =~ ^[Yy]$ ]]; then
    info_msg "가상환경 생성 중..."
    python3 -m venv venv
    check_error "가상환경 생성 실패"
    
    info_msg "가상환경 활성화 중..."
    source venv/bin/activate
    check_error "가상환경 활성화 실패"
    
    success_msg "가상환경 생성 및 활성화 완료"
    VENV_CREATED=true
else
    VENV_CREATED=false
fi

# 6. 의존성 패키지 설치
info_msg "의존성 패키지 설치 중..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    check_error "requirements.txt에서 패키지 설치 실패"
else
    # requirements.txt가 없으면 개별 설치
    pip3 install websockets numpy pandas scikit-learn joblib aiofiles typing-extensions
    check_error "개별 패키지 설치 실패"
fi
success_msg "의존성 패키지 설치 완료"

# 7. 방화벽 설정 (선택사항)
read -p "방화벽에서 포트 8765를 열겠습니까? (y/n): " open_firewall
if [[ $open_firewall =~ ^[Yy]$ ]]; then
    info_msg "방화벽 포트 8765 열기 중..."
    sudo ufw allow 8765
    success_msg "방화벽 설정 완료"
fi

# 8. 환경 설정 파일 생성
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    info_msg "환경 설정 파일 생성 중..."
    cp .env.example .env
    success_msg "환경 설정 파일(.env) 생성 완료"
fi

# 9. 실행 권한 부여
info_msg "실행 권한 설정 중..."
chmod +x main.py
chmod +x test_client.py
chmod +x simple_test.py
success_msg "실행 권한 설정 완료"

# 10. 설치 완료 메시지
echo ""
echo "========================================"
echo -e "${GREEN}설치가 성공적으로 완료되었습니다!${NC}"
echo "========================================"
echo ""
echo "서버 실행 방법:"
if [ "$VENV_CREATED" = true ]; then
    echo "1. 가상환경 활성화: source venv/bin/activate"
    echo "2. 서버 실행: python3 main.py"
else
    echo "1. 서버 실행: python3 main.py"
fi
echo ""
echo "백그라운드 실행: nohup python3 main.py > server.log 2>&1 &"
echo "서버 중지: pkill -f main.py"
echo ""
echo "테스트 클라이언트 실행: python3 test_client.py"
echo ""
echo "로그 확인: tail -f logs/posture_server.log"
echo ""
echo -e "${YELLOW}주의: .env 파일에서 필요에 따라 설정을 변경하세요${NC}"
echo ""