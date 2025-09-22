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
sudo apt install -y python3 python3-pip python3-venv python3-dev python3-full
check_error "Python3 설치 실패"
success_msg "Python3 설치 완료"

# 3. Python 버전 확인
python3_version=$(python3 --version)
info_msg "설치된 Python 버전: $python3_version"

# 4. PEP 668 확인 및 가상환경 생성 권장
info_msg "PEP 668 호환성 확인 중..."
if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    info_msg "Python 3.11+ 감지: 가상환경 사용을 강력히 권장합니다"
    create_venv=y
else
    read -p "가상환경을 생성하시겠습니까? (y/n): " create_venv
fi
# 5. 가상환경 생성 및 패키지 설치
if [[ $create_venv =~ ^[Yy]$ ]]; then
    info_msg "가상환경 생성 중..."
    python3 -m venv venv
    check_error "가상환경 생성 실패"
    
    info_msg "가상환경 활성화 중..."
    source venv/bin/activate
    check_error "가상환경 활성화 실패"
    
    success_msg "가상환경 생성 및 활성화 완료"
    
    # 가상환경 내에서 pip 업그레이드
    info_msg "가상환경 내 pip 업그레이드 중..."
    pip install --upgrade pip
    check_error "pip 업그레이드 실패"
    
    # 가상환경 내에서 패키지 설치
    info_msg "Python 패키지 설치 중..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        check_error "requirements.txt에서 패키지 설치 실패"
    else
        pip install websockets numpy pandas scikit-learn joblib aiofiles typing-extensions
        check_error "개별 패키지 설치 실패"
    fi
    
    VENV_CREATED=true
else
    # 시스템 전역 설치 시도 (PEP 668 우회 방법들)
    warn_msg "시스템 전역 설치를 시도합니다."
    info_msg "PEP 668 오류가 발생하면 가상환경 사용을 권장합니다."
    
    # 첫 번째 시도: 시스템 패키지 관리자 사용
    info_msg "시스템 패키지로 websockets 설치 시도 중..."
    if sudo apt install -y python3-websockets python3-numpy python3-pandas python3-sklearn 2>/dev/null; then
        info_msg "시스템 패키지로 일부 라이브러리 설치 완료"
    fi
    
    # 두 번째 시도: pipx 사용 (있다면)
    if command -v pipx >/dev/null 2>&1; then
        info_msg "pipx로 패키지 설치 시도 중..."
        pipx install websockets --force 2>/dev/null || true
    fi
    
    # 세 번째 시도: --break-system-packages 플래그 사용
    info_msg "pip로 패키지 설치 중 (시스템 패키지 우회)..."
    if [ -f "requirements.txt" ]; then
        python3 -m pip install -r requirements.txt --break-system-packages 2>/dev/null || {
            warn_msg "시스템 패키지 설치 실패. 가상환경을 사용하세요:"
            echo "  python3 -m venv venv"
            echo "  source venv/bin/activate"
            echo "  pip install -r requirements.txt"
        }
    else
        python3 -m pip install websockets numpy pandas scikit-learn joblib aiofiles typing-extensions --break-system-packages 2>/dev/null || {
            warn_msg "시스템 패키지 설치 실패. 가상환경을 사용하세요."
        }
    fi
    
    VENV_CREATED=false
fi

success_msg "의존성 패키지 설치 완료"

# 7. 방화벽 설정 (선택사항)
read -p "방화벽에서 포트 8765를 열겠습니까? (y/n): " open_firewall
if [[ $open_firewall =~ ^[Yy]$ ]]; then
    info_msg "방화벽 포트 8765 열기 중..."
    sudo ufw allow 8765
    success_msg "방화벽 설정 완료"
fi

# 8. 권한 설정
info_msg "스크립트 권한 설정 중..."
chmod +x server_manager.sh
success_msg "권한 설정 완료"

echo ""
success_msg "🎉 Soft Electronic Server 설치 완료!"
echo ""

if [ "$VENV_CREATED" = true ]; then
    info_msg "가상환경 설치가 완료되었습니다."
    echo "서버를 실행하려면:"
    echo "  cd $(pwd)"
    echo "  source venv/bin/activate"
    echo "  python3 main.py"
    echo ""
    echo "또는 서버 관리 스크립트 사용:"
    echo "  source venv/bin/activate"
    echo "  ./server_manager.sh start"
    echo ""
    info_msg "가상환경 비활성화: deactivate"
else
    info_msg "시스템 전역 설치가 완료되었습니다."
    echo "서버를 실행하려면:"
    echo "  python3 main.py"
    echo ""
    echo "또는 서버 관리 스크립트 사용:"
    echo "  ./server_manager.sh start"
    echo ""
    warn_msg "PEP 668 오류가 발생했다면 가상환경을 사용하세요:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
fi

echo ""
info_msg "서버 관리 명령어:"
echo "  ./server_manager.sh start   - 서버 시작"
echo "  ./server_manager.sh stop    - 서버 중지"
echo "  ./server_manager.sh status  - 서버 상태 확인"
echo "  ./server_manager.sh restart - 서버 재시작"
echo ""
success_msg "설치 스크립트 실행 완료!"

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