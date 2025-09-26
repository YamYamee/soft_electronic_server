"""
자세 인식 시스템 통계 API
각 자세별 시간 통계 및 분석 기능 제공
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import struct
from config import config

# 로거 설정
logger = logging.getLogger(__name__)

# 바이트 데이터 변환 헬퍼 함수
def safe_int_convert(value):
    """바이트 또는 다른 타입의 데이터를 안전하게 정수로 변환"""
    if isinstance(value, bytes):
        # 바이트 데이터를 정수로 변환 (little-endian으로 가정)
        try:
            if len(value) == 8:
                return struct.unpack('<Q', value)[0]  # unsigned long long
            elif len(value) == 4:
                return struct.unpack('<I', value)[0]  # unsigned int
            elif len(value) == 2:
                return struct.unpack('<H', value)[0]  # unsigned short
            elif len(value) == 1:
                return struct.unpack('<B', value)[0]  # unsigned char
            else:
                # 바이트 길이가 예상과 다른 경우, 첫 바이트만 사용
                return struct.unpack('<B', value[:1])[0]
        except struct.error:
            logger.warning(f"바이트 변환 실패, 기본값 0 반환: {value}")
            return 0
    elif isinstance(value, (int, float)):
        return int(value)
    elif isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            logger.warning(f"문자열을 정수로 변환 실패, 기본값 0 반환: {value}")
            return 0
    else:
        logger.warning(f"알 수 없는 타입을 정수로 변환, 기본값 0 반환: {type(value)} - {value}")
        return 0

def safe_float_convert(value):
    """바이트 또는 다른 타입의 데이터를 안전하게 실수로 변환"""
    if isinstance(value, bytes):
        # 먼저 정수로 변환한 다음 실수로 변환
        return float(safe_int_convert(value))
    elif isinstance(value, (int, float)):
        return float(value)
    elif isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            logger.warning(f"문자열을 실수로 변환 실패, 기본값 0.0 반환: {value}")
            return 0.0
    else:
        logger.warning(f"알 수 없는 타입을 실수로 변환, 기본값 0.0 반환: {type(value)} - {value}")
        return 0.0

def safe_str_convert(value):
    """바이트 또는 다른 타입의 데이터를 안전하게 문자열로 변환"""
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            logger.warning(f"바이트를 문자열로 디코딩 실패, repr 사용: {value}")
            return repr(value)
    elif value is None:
        return ""
    else:
        return str(value)

# FastAPI 앱 생성
app = FastAPI(
    title="자세 인식 통계 API",
    description="실시간 자세 분석 통계 및 점수 시스템",
    version="1.0.0"
)

# API 요청 로깅 미들웨어
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    
    # 요청 정보 로깅
    method = request.method
    path = request.url.path
    client_ip = request.client.host if request.client else "unknown"
    
    from logger_config import log_api_request
    log_api_request(path, method, client_ip)
    
    # 응답 처리
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(f"API 응답: {method} {path} - {response.status_code} ({process_time*1000:.1f}ms)")
    
    return response

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 응답 모델 정의
class PostureTimeStats(BaseModel):
    posture_id: int
    posture_name: str
    total_duration_minutes: float
    session_count: int
    average_session_duration: float
    percentage: float
    first_detected: Optional[str] = None
    last_detected: Optional[str] = None

class DailyStats(BaseModel):
    date: str
    total_time_minutes: float
    posture_breakdown: List[PostureTimeStats]
    most_common_posture: str
    worst_posture_duration: float

class PostureSession(BaseModel):
    session_id: int
    posture_id: int
    posture_name: str
    start_time: str
    end_time: str
    duration_minutes: float
    confidence: float

class StatsSummary(BaseModel):
    total_monitoring_time: float
    total_sessions: int
    average_session_duration: float
    good_posture_percentage: float
    most_problematic_posture: str
    data_period: str

class PostureScore(BaseModel):
    date: str
    total_score: int
    good_posture_score: int
    bad_posture_penalty: int
    session_stability_score: int
    monitoring_time_minutes: float
    good_posture_percentage: float
    worst_posture: str
    worst_posture_duration: float
    grade: str
    feedback: str

class DataResetResponse(BaseModel):
    success: bool
    message: str
    deleted_records: int
    reset_timestamp: str

# 자세 라벨 매핑 (업데이트된 8가지 자세)
POSTURE_LABELS = {
    0: "바른 자세",
    1: "거북목 자세", 
    2: "목 숙이기",
    3: "앞으로 당겨 기대기",
    4: "오른쪽으로 기대기",
    5: "왼쪽으로 기대기",
    6: "오른쪽 다리 꼭기", 
    7: "왼쪽 다리 꼭기"
}

class StatisticsDatabase:
    """통계 전용 데이터베이스 클래스"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or config.DATABASE_PATH
    
    def get_db_connection(self):
        """데이터베이스 연결 반환"""
        return sqlite3.connect(self.db_path)
    
    def calculate_posture_durations(self, start_date: str = None, end_date: str = None, device_id: str = None) -> List[Dict]:
        """자세별 지속 시간 계산"""
        try:
            with self.get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 기본 쿼리
                query = """
                    SELECT 
                        predicted_posture,
                        timestamp,
                        confidence,
                        device_id,
                        ROW_NUMBER() OVER (ORDER BY timestamp) as row_num
                    FROM posture_predictions 
                    WHERE 1=1
                """
                params = []
                
                # 필터 조건 추가
                if start_date:
                    query += " AND date(timestamp) >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND date(timestamp) <= ?"
                    params.append(end_date)
                
                if device_id:
                    query += " AND device_id = ?"
                    params.append(device_id)
                
                query += " ORDER BY timestamp"
                
                cursor.execute(query, params)
                records = cursor.fetchall()
                
                if not records:
                    return []
                
                # 자세 세션 계산 (연속된 같은 자세를 하나의 세션으로 간주)
                sessions = []
                current_posture = None
                session_start = None
                session_confidences = []
                
                for record in records:
                    timestamp = datetime.strptime(record['timestamp'], '%Y-%m-%d %H:%M:%S')
                    posture = safe_int_convert(record['predicted_posture'])
                    confidence = record['confidence']
                    
                    if current_posture != posture:
                        # 이전 세션 종료
                        if current_posture is not None and session_start is not None:
                            duration = (timestamp - session_start).total_seconds() / 60  # 분 단위
                            if duration > 0:  # 0분 이상의 세션만 기록
                                sessions.append({
                                    'posture_id': current_posture,
                                    'posture_name': POSTURE_LABELS.get(current_posture, f'Unknown_{current_posture}'),
                                    'start_time': session_start.isoformat(),
                                    'end_time': timestamp.isoformat(),
                                    'duration_minutes': round(duration, 2),
                                    'avg_confidence': round(sum(session_confidences) / len(session_confidences), 3) if session_confidences else 0
                                })
                        
                        # 새 세션 시작
                        current_posture = posture
                        session_start = timestamp
                        session_confidences = [confidence]
                    else:
                        session_confidences.append(confidence)
                
                # 마지막 세션 처리
                if current_posture is not None and session_start is not None:
                    # 마지막 기록의 시간을 사용하거나 현재 시간 사용
                    last_timestamp = datetime.strptime(records[-1]['timestamp'], '%Y-%m-%d %H:%M:%S')
                    duration = (last_timestamp - session_start).total_seconds() / 60
                    if duration > 0:
                        sessions.append({
                            'posture_id': current_posture,
                            'posture_name': POSTURE_LABELS.get(current_posture, f'Unknown_{current_posture}'),
                            'start_time': session_start.isoformat(),
                            'end_time': last_timestamp.isoformat(),
                            'duration_minutes': round(duration, 2),
                            'avg_confidence': round(sum(session_confidences) / len(session_confidences), 3) if session_confidences else 0
                        })
                
                return sessions
                
        except Exception as e:
            logger.error(f"자세 지속시간 계산 오류: {e}")
            raise
    
    def get_posture_statistics(self, start_date: str = None, end_date: str = None, device_id: str = None) -> List[PostureTimeStats]:
        """자세별 통계 요약"""
        sessions = self.calculate_posture_durations(start_date, end_date, device_id)
        
        if not sessions:
            return []
        
        # 자세별 통계 집계
        posture_stats = {}
        total_time = 0
        
        for session in sessions:
            posture_id = session['posture_id']
            duration = session['duration_minutes']
            total_time += duration
            
            if posture_id not in posture_stats:
                posture_stats[posture_id] = {
                    'posture_id': posture_id,
                    'posture_name': session['posture_name'],
                    'total_duration': 0,
                    'session_count': 0,
                    'confidences': [],
                    'first_detected': session['start_time'],
                    'last_detected': session['end_time']
                }
            
            posture_stats[posture_id]['total_duration'] += duration
            posture_stats[posture_id]['session_count'] += 1
            posture_stats[posture_id]['confidences'].append(session['avg_confidence'])
            posture_stats[posture_id]['last_detected'] = session['end_time']
        
        # PostureTimeStats 객체로 변환 (안전한 데이터 타입 변환)
        result = []
        for stats in posture_stats.values():
            posture_id = safe_int_convert(stats['posture_id'])
            total_duration = safe_float_convert(stats['total_duration'])
            session_count = safe_int_convert(stats['session_count'])
            
            result.append(PostureTimeStats(
                posture_id=posture_id,
                posture_name=safe_str_convert(stats['posture_name']),
                total_duration_minutes=round(total_duration, 2),
                session_count=session_count,
                average_session_duration=round(total_duration / session_count, 2) if session_count > 0 else 0,
                percentage=round((total_duration / total_time * 100), 2) if total_time > 0 else 0,
                first_detected=safe_str_convert(stats['first_detected']),
                last_detected=safe_str_convert(stats['last_detected'])
            ))
        
        # 총 시간 기준으로 정렬
        result.sort(key=lambda x: x.total_duration_minutes, reverse=True)
        return result
    
    def calculate_daily_posture_score(self, date: str, device_id: str = None) -> Dict:
        """오늘의 자세 점수 계산 (100점 만점)"""
        try:
            posture_stats = self.get_posture_statistics(date, date, device_id)
            
            if not posture_stats:
                return {
                    'total_score': 0,
                    'good_posture_score': 0,
                    'bad_posture_penalty': 0,
                    'session_stability_score': 0,
                    'monitoring_time': 0,
                    'good_posture_percentage': 0,
                    'worst_posture': '데이터 없음',
                    'worst_posture_duration': 0,
                    'grade': 'F',
                    'feedback': '측정된 데이터가 없습니다.'
                }
            
            total_time = sum(stat.total_duration_minutes for stat in posture_stats)
            
            # 1. 바른 자세 점수 (60점 만점)
            good_posture = next((stat for stat in posture_stats if stat.posture_id == 0), None)
            good_posture_percentage = good_posture.percentage if good_posture else 0
            good_posture_score = min(60, int(good_posture_percentage * 0.6))
            
            # 2. 나쁜 자세 감점 (최대 -40점)
            bad_postures = [stat for stat in posture_stats if stat.posture_id != 0]
            bad_posture_penalty = 0
            worst_posture = '없음'
            worst_posture_duration = 0
            
            if bad_postures:
                # 자세별 가중치 (더 해로운 자세일수록 높은 감점)
                posture_weights = {
                    1: 4,  # 거북목 자세 (매우 해로움)
                    2: 3,  # 목 숙이기 (해로움)
                    3: 3,  # 앞으로 당겨 기대기 (해로움)
                    4: 2,  # 오른쪽으로 기대기 (보통)
                    5: 2,  # 왼쪽으로 기대기 (보통)
                    6: 1,  # 오른쪽 다리 꼭기 (가벼움)
                    7: 1   # 왼쪽 다리 꼭기 (가벼움)
                }
                
                for stat in bad_postures:
                    weight = posture_weights.get(stat.posture_id, 2)
                    # 시간 비율에 따른 감점 (더 오래할수록 더 큰 감점)
                    time_penalty = (stat.total_duration_minutes / total_time) * 100 * weight * 0.15
                    bad_posture_penalty += time_penalty
                
                bad_posture_penalty = min(40, int(bad_posture_penalty))
                
                # 가장 문제가 되는 자세 (가중치 × 시간 기준)
                worst_stat = max(bad_postures, 
                    key=lambda x: x.total_duration_minutes * posture_weights.get(x.posture_id, 2))
                worst_posture = worst_stat.posture_name
                worst_posture_duration = worst_stat.total_duration_minutes
            
            # 3. 세션 패턴 분석 및 보너스 점수 (20점 만점)
            total_sessions = sum(stat.session_count for stat in posture_stats)
            avg_session_duration = total_time / total_sessions if total_sessions > 0 else 0
            
            # 세션 안정성 점수 (10점)
            if 5 <= avg_session_duration <= 15:
                stability_base = 10
            elif 3 <= avg_session_duration < 5 or 15 < avg_session_duration <= 20:
                stability_base = 8
            elif 1 <= avg_session_duration < 3 or 20 < avg_session_duration <= 30:
                stability_base = 5
            else:
                stability_base = 2
            
            # 사용 빈도 보너스 (10점) - 적절한 모니터링 빈도
            if total_sessions >= 3:  # 하루에 3회 이상 모니터링
                frequency_bonus = 10
            elif total_sessions >= 2:
                frequency_bonus = 7
            elif total_sessions >= 1:
                frequency_bonus = 5
            else:
                frequency_bonus = 0
                
            session_stability_score = stability_base + frequency_bonus
            
            # 4. 총점 계산 (100점 만점)
            total_score = max(0, min(100, good_posture_score - bad_posture_penalty + session_stability_score))
            
            # 5. 등급 및 맞춤형 피드백
            if total_score >= 85:
                grade = 'A+'
                feedback = '🌟 완벽한 자세! 오늘 하루 정말 잘 하셨습니다!'
            elif total_score >= 75:
                grade = 'A'
                feedback = '😊 훌륭한 자세! 조금만 더 신경쓰면 완벽해요!'
            elif total_score >= 65:
                grade = 'B+'
                feedback = '👍 좋은 자세! 바른 자세를 조금 더 유지해보세요.'
            elif total_score >= 55:
                grade = 'B'
                feedback = '😐 보통 자세. 의식적으로 자세를 교정해보세요.'
            elif total_score >= 45:
                grade = 'C+'
                feedback = '😟 자세 개선이 필요해요. 특히 {}을(를) 줄여보세요. ({}분 지속)'.format(worst_posture, int(worst_posture_duration))
            elif total_score >= 35:
                grade = 'C'
                feedback = '🚨 자세에 주의가 필요합니다. {}을(를) 자주 하고 있어요. ({}분 지속)'.format(worst_posture, int(worst_posture_duration))
            else:
                grade = 'D'
                if worst_posture != '없음':
                    feedback = '⚠️ 자세가 매우 좋지 않습니다. {}을(를) {}분간 지속했습니다. 즉시 개선이 필요해요!'.format(worst_posture, int(worst_posture_duration))
                else:
                    feedback = '⚠️ 자세가 매우 좋지 않습니다. 바른 자세를 의식적으로 유지하세요!'
            
            return {
                'total_score': total_score,
                'good_posture_score': good_posture_score,
                'bad_posture_penalty': bad_posture_penalty,
                'session_stability_score': session_stability_score,
                'monitoring_time': round(total_time, 2),
                'good_posture_percentage': round(good_posture_percentage, 2),
                'worst_posture': worst_posture,
                'worst_posture_duration': round(worst_posture_duration, 2),
                'grade': grade,
                'feedback': feedback
            }
            
        except Exception as e:
            logger.error(f"자세 점수 계산 오류: {e}")
            raise
    
    def reset_all_data(self) -> Dict:
        """모든 예측 데이터 삭제"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 삭제할 레코드 수 확인
                cursor.execute("SELECT COUNT(*) FROM posture_predictions")
                total_records = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM client_connections")
                connection_records = cursor.fetchone()[0]
                
                # 데이터 삭제
                cursor.execute("DELETE FROM posture_predictions")
                cursor.execute("DELETE FROM client_connections")
                
                # 인덱스 리셋
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='posture_predictions'")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='client_connections'")
                
                conn.commit()
                
                deleted_count = total_records + connection_records
                
                logger.info(f"데이터 초기화 완료: {deleted_count}개 레코드 삭제")
                
                return {
                    'success': True,
                    'deleted_records': deleted_count,
                    'message': f'성공적으로 {deleted_count}개 레코드를 삭제했습니다.'
                }
                
        except Exception as e:
            logger.error(f"데이터 초기화 오류: {e}")
            return {
                'success': False,
                'deleted_records': 0,
                'message': f'데이터 초기화 실패: {str(e)}'
            }

# 데이터베이스 인스턴스
stats_db = StatisticsDatabase()

# API 엔드포인트 정의

@app.get("/", tags=["Root"])
async def root():
    """API 상태 확인"""
    return {
        "message": "자세 인식 통계 API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """헬스 체크"""
    try:
        with stats_db.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM posture_predictions")
            total_records = cursor.fetchone()[0]
        
        return {
            "status": "healthy",
            "database": "connected",
            "total_records": total_records,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@app.get("/statistics/postures", response_model=List[PostureTimeStats], tags=["Statistics"])
async def get_posture_statistics(
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    device_id: Optional[str] = Query(None, description="디바이스 ID")
):
    """
    자세별 시간 통계 조회
    
    - **start_date**: 통계 기간 시작일 (미지정시 전체 기간)
    - **end_date**: 통계 기간 종료일 (미지정시 현재까지)
    - **device_id**: 특정 디바이스의 데이터만 조회 (미지정시 전체 디바이스)
    """
    try:
        return stats_db.get_posture_statistics(start_date, end_date, device_id)
    except Exception as e:
        logger.error(f"자세 통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics/daily/{date}", response_model=DailyStats, tags=["Statistics"])
async def get_daily_statistics(
    date: str,
    device_id: Optional[str] = Query(None, description="디바이스 ID")
):
    """
    특정 날짜의 자세 통계 조회
    
    - **date**: 조회할 날짜 (YYYY-MM-DD)
    - **device_id**: 특정 디바이스의 데이터만 조회
    """
    try:
        # 해당 날짜의 통계 조회
        posture_stats = stats_db.get_posture_statistics(date, date, device_id)
        
        if not posture_stats:
            raise HTTPException(status_code=404, detail=f"No data found for date: {date}")
        
        total_time = sum(stat.total_duration_minutes for stat in posture_stats)
        most_common = max(posture_stats, key=lambda x: x.total_duration_minutes)
        
        # 가장 문제가 되는 자세 (바른 자세가 아닌 것 중 가장 오래한 것)
        bad_postures = [stat for stat in posture_stats if stat.posture_id != 0]
        worst_posture_duration = max(bad_postures, key=lambda x: x.total_duration_minutes).total_duration_minutes if bad_postures else 0
        
        return DailyStats(
            date=date,
            total_time_minutes=round(total_time, 2),
            posture_breakdown=posture_stats,
            most_common_posture=most_common.posture_name,
            worst_posture_duration=worst_posture_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"일일 통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics/sessions", response_model=List[PostureSession], tags=["Statistics"])
async def get_posture_sessions(
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    device_id: Optional[str] = Query(None, description="디바이스 ID"),
    limit: int = Query(100, description="최대 반환 세션 수")
):
    """
    자세 세션 목록 조회 (각 연속된 자세의 시간 구간)
    
    - **start_date**: 조회 기간 시작일
    - **end_date**: 조회 기간 종료일  
    - **device_id**: 특정 디바이스 필터
    - **limit**: 최대 반환할 세션 수
    """
    try:
        sessions = stats_db.calculate_posture_durations(start_date, end_date, device_id)
        
        # 세션 ID 추가 및 PostureSession 객체로 변환
        result = []
        for i, session in enumerate(sessions[-limit:]):  # 최근 limit개만
            result.append(PostureSession(
                session_id=i + 1,
                posture_id=session['posture_id'],
                posture_name=session['posture_name'],
                start_time=session['start_time'],
                end_time=session['end_time'],
                duration_minutes=session['duration_minutes'],
                confidence=session['avg_confidence']
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"세션 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics/summary", response_model=StatsSummary, tags=["Statistics"])
async def get_statistics_summary(
    days: int = Query(7, description="최근 몇 일간의 데이터"),
    device_id: Optional[str] = Query(None, description="디바이스 ID")
):
    """
    통계 요약 정보
    
    - **days**: 최근 며칠간의 데이터를 요약할지 (기본 7일)
    - **device_id**: 특정 디바이스의 데이터만 조회
    """
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        posture_stats = stats_db.get_posture_statistics(
            str(start_date), str(end_date), device_id
        )
        
        if not posture_stats:
            return StatsSummary(
                total_monitoring_time=0,
                total_sessions=0,
                average_session_duration=0,
                good_posture_percentage=0,
                most_problematic_posture="데이터 없음",
                data_period=f"{start_date} ~ {end_date}"
            )
        
        total_time = sum(stat.total_duration_minutes for stat in posture_stats)
        total_sessions = sum(stat.session_count for stat in posture_stats)
        avg_session_duration = total_time / total_sessions if total_sessions > 0 else 0
        
        # 바른 자세 비율
        good_posture = next((stat for stat in posture_stats if stat.posture_id == 0), None)
        good_posture_percentage = good_posture.percentage if good_posture else 0
        
        # 가장 문제가 되는 자세 (바른 자세 제외하고 가장 오래)
        bad_postures = [stat for stat in posture_stats if stat.posture_id != 0]
        most_problematic = max(bad_postures, key=lambda x: x.total_duration_minutes).posture_name if bad_postures else "없음"
        
        return StatsSummary(
            total_monitoring_time=round(total_time, 2),
            total_sessions=total_sessions,
            average_session_duration=round(avg_session_duration, 2),
            good_posture_percentage=round(good_posture_percentage, 2),
            most_problematic_posture=most_problematic,
            data_period=f"{start_date} ~ {end_date}"
        )
        
    except Exception as e:
        logger.error(f"통계 요약 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics/score/today", response_model=PostureScore, tags=["Statistics"])
async def get_today_posture_score(
    device_id: Optional[str] = Query(None, description="디바이스 ID")
):
    """
    오늘의 자세 점수 조회 (100점 만점)
    
    - **device_id**: 특정 디바이스의 데이터만 조회
    
    점수 구성:
    - 바른 자세 비율 (60점)
    - 나쁜 자세 감점 (최대 -30점)
    - 세션 안정성 (20점)
    """
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        score_data = stats_db.calculate_daily_posture_score(today, device_id)
        
        return PostureScore(
            date=today,
            total_score=score_data['total_score'],
            good_posture_score=score_data['good_posture_score'],
            bad_posture_penalty=score_data['bad_posture_penalty'],
            session_stability_score=score_data['session_stability_score'],
            monitoring_time_minutes=score_data['monitoring_time'],
            good_posture_percentage=score_data['good_posture_percentage'],
            worst_posture=score_data['worst_posture'],
            worst_posture_duration=score_data['worst_posture_duration'],
            grade=score_data['grade'],
            feedback=score_data['feedback']
        )
        
    except Exception as e:
        logger.error(f"오늘의 자세 점수 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics/score/{date}", response_model=PostureScore, tags=["Statistics"])
async def get_date_posture_score(
    date: str,
    device_id: Optional[str] = Query(None, description="디바이스 ID")
):
    """
    특정 날짜의 자세 점수 조회 (100점 만점)
    
    - **date**: 조회할 날짜 (YYYY-MM-DD)
    - **device_id**: 특정 디바이스의 데이터만 조회
    """
    try:
        score_data = stats_db.calculate_daily_posture_score(date, device_id)
        
        return PostureScore(
            date=date,
            total_score=score_data['total_score'],
            good_posture_score=score_data['good_posture_score'],
            bad_posture_penalty=score_data['bad_posture_penalty'],
            session_stability_score=score_data['session_stability_score'],
            monitoring_time_minutes=score_data['monitoring_time'],
            good_posture_percentage=score_data['good_posture_percentage'],
            worst_posture=score_data['worst_posture'],
            worst_posture_duration=score_data['worst_posture_duration'],
            grade=score_data['grade'],
            feedback=score_data['feedback']
        )
        
    except Exception as e:
        logger.error(f"자세 점수 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/data/reset", response_model=DataResetResponse, tags=["Management"])
async def reset_all_data(
    confirm: bool = Query(False, description="삭제 확인 (true여야 실행됨)")
):
    """
    모든 예측 데이터 삭제 (주의: 복구 불가능)
    
    - **confirm**: 반드시 true로 설정해야 실행됩니다
    
    ⚠️ 경고: 이 작업은 되돌릴 수 없습니다!
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="데이터 삭제를 위해 confirm=true 파라미터가 필요합니다"
        )
    
    try:
        result = stats_db.reset_all_data()
        
        return DataResetResponse(
            success=result['success'],
            message=result['message'],
            deleted_records=result['deleted_records'],
            reset_timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"데이터 초기화 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/postures", tags=["Reference"])
async def get_posture_labels():
    """자세 분류 라벨 목록"""
    return {
        "postures": [
            {"id": pid, "name": name} 
            for pid, name in POSTURE_LABELS.items()
        ],
        "total_postures": len(POSTURE_LABELS)
    }

@app.get("/statistics/prediction", tags=["Statistics"])
async def get_prediction_statistics(
    hours: int = Query(24, description="통계 조회 기간 (시간)", ge=1, le=168)
):
    """
    예측 모델 성능 통계
    
    - **hours**: 통계 조회 기간 (기본값: 24시간, 최대: 1주일)
    
    예측 방법별 통계, 모델별 성능, 처리 시간 등을 제공합니다.
    """
    try:
        from model_predictor import predictor
        
        stats = predictor.get_prediction_statistics(hours)
        
        return {
            "period_hours": hours,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"예측 통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics/prediction/logs", tags=["Statistics"])
async def get_recent_prediction_logs(
    limit: int = Query(100, description="조회할 로그 수", ge=1, le=1000),
    hours: int = Query(24, description="조회 기간 (시간)", ge=1, le=168)
):
    """
    최근 예측 로그 조회
    
    - **limit**: 조회할 로그 수 (기본값: 100, 최대: 1000)
    - **hours**: 조회 기간 (기본값: 24시간)
    
    개별 예측 결과의 상세 로그를 제공합니다.
    """
    try:
        with stats_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    timestamp, client_id, device_id,
                    ensemble_prediction, ensemble_confidence,
                    prediction_method, processing_time_ms,
                    lr_prediction, lr_confidence,
                    rf_prediction, rf_confidence,
                    dt_prediction, dt_confidence,
                    kn_prediction, kn_confidence,
                    voting_scores, models_used
                FROM prediction_logs 
                WHERE timestamp >= datetime('now', '-{} hours')
                ORDER BY timestamp DESC 
                LIMIT ?
            '''.format(hours), (limit,))
            
            logs = []
            for row in cursor.fetchall():
                import json
                log_entry = {
                    'timestamp': safe_str_convert(row[0]),
                    'client_id': safe_str_convert(row[1]),
                    'device_id': safe_str_convert(row[2]),
                    'prediction': safe_int_convert(row[3]),
                    'confidence': safe_float_convert(row[4]),
                    'method': safe_str_convert(row[5]),
                    'processing_time_ms': safe_float_convert(row[6]),
                    'individual_models': {
                        'lr': {'prediction': safe_int_convert(row[7]), 'confidence': safe_float_convert(row[8])},
                        'rf': {'prediction': safe_int_convert(row[9]), 'confidence': safe_float_convert(row[10])},
                        'dt': {'prediction': safe_int_convert(row[11]), 'confidence': safe_float_convert(row[12])},
                        'kn': {'prediction': safe_int_convert(row[13]), 'confidence': safe_float_convert(row[14])}
                    },
                    'voting_scores': json.loads(safe_str_convert(row[15])) if row[15] else None,
                    'models_used': json.loads(row[16]) if row[16] else []
                }
                logs.append(log_entry)
            
            return {
                "logs": logs,
                "total_count": len(logs),
                "period_hours": hours,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"예측 로그 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "statistics_api:app",
        host="0.0.0.0",
        port=8766,
        reload=True,
        log_level="info"
    )