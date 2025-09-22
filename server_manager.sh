#!/bin/bash

# 자세 인식 WebSocket 서버 관리 스크립트
# 사용법: bash server_manager.sh [start|stop|restart|status|logs]

SERVER_SCRIPT="main.py"
LOG_FILE="server.log"
PID_FILE="server.pid"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
start_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}서버가 이미 실행 중입니다 (PID: $PID)${NC}"
            return 1
        else
            rm -f "$PID_FILE"
        fi
    fi
    
    echo -e "${BLUE}서버를 시작합니다...${NC}"
    
    # 가상환경 확인 및 활성화
    if [ -d "venv" ]; then
        echo -e "${YELLOW}가상환경을 활성화합니다...${NC}"
        source venv/bin/activate
    fi
    
    # 백그라운드에서 서버 실행
    nohup python3 "$SERVER_SCRIPT" > "$LOG_FILE" 2>&1 &
    SERVER_PID=$!
    
    # PID 저장
    echo $SERVER_PID > "$PID_FILE"
    
    # 잠시 대기 후 상태 확인
    sleep 2
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 서버가 성공적으로 시작되었습니다 (PID: $SERVER_PID)${NC}"
        echo -e "${BLUE}로그 확인: tail -f $LOG_FILE${NC}"
    else
        echo -e "${RED}✗ 서버 시작에 실패했습니다${NC}"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_server() {
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${YELLOW}서버가 실행 중이지 않습니다${NC}"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${BLUE}서버를 중지합니다... (PID: $PID)${NC}"
        kill $PID
        
        # 종료 대기 (최대 10초)
        for i in {1..10}; do
            if ! ps -p $PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # 강제 종료가 필요한 경우
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}강제 종료 중...${NC}"
            kill -9 $PID
        fi
        
        rm -f "$PID_FILE"
        echo -e "${GREEN}✓ 서버가 중지되었습니다${NC}"
    else
        echo -e "${YELLOW}서버 프로세스를 찾을 수 없습니다${NC}"
        rm -f "$PID_FILE"
    fi
}

restart_server() {
    echo -e "${BLUE}서버를 재시작합니다...${NC}"
    stop_server
    sleep 2
    start_server
}

show_status() {
    echo -e "${BLUE}서버 상태 확인:${NC}"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${GREEN}✓ 서버가 실행 중입니다 (PID: $PID)${NC}"
            
            # 메모리 사용량 확인
            MEMORY=$(ps -p $PID -o rss= | awk '{print $1/1024 "MB"}')
            echo -e "${BLUE}  메모리 사용량: $MEMORY${NC}"
            
            # 실행 시간 확인
            ETIME=$(ps -p $PID -o etime= | tr -d ' ')
            echo -e "${BLUE}  실행 시간: $ETIME${NC}"
            
            # 포트 확인
            PORT_STATUS=$(netstat -tlnp 2>/dev/null | grep ":8765 " | grep "$PID")
            if [ ! -z "$PORT_STATUS" ]; then
                echo -e "${GREEN}  포트 8765: 활성${NC}"
            else
                echo -e "${YELLOW}  포트 8765: 비활성${NC}"
            fi
        else
            echo -e "${RED}✗ 서버가 실행 중이지 않습니다${NC}"
            rm -f "$PID_FILE"
        fi
    else
        echo -e "${YELLOW}PID 파일이 없습니다. 서버가 실행 중이지 않습니다.${NC}"
    fi
    
    # 로그 파일 상태
    if [ -f "$LOG_FILE" ]; then
        LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
        echo -e "${BLUE}  로그 파일 크기: $LOG_SIZE${NC}"
    fi
}

show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${BLUE}최근 로그 (실시간 모니터링하려면 Ctrl+C로 종료):${NC}"
        tail -f "$LOG_FILE"
    else
        echo -e "${YELLOW}로그 파일이 없습니다${NC}"
    fi
}

# 메인 로직
case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "사용법: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "명령어 설명:"
        echo "  start   - 서버 시작"
        echo "  stop    - 서버 중지"
        echo "  restart - 서버 재시작"
        echo "  status  - 서버 상태 확인"
        echo "  logs    - 로그 실시간 확인"
        exit 1
        ;;
esac

exit 0