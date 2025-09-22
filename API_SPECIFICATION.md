# 자세 인식 통계 API 명세서

## 개요

이 API는 자세 인식 시스템에서 수집된 데이터를 바탕으로 각 자세별 시간 통계 및 분석 기능을 제공합니다.

### 서버 정보
- **Base URL**: `http://localhost:8766` (또는 `http://3.34.159.75:8766`)
- **API Version**: 1.0.0
- **Protocol**: HTTP/HTTPS
- **Content-Type**: application/json

### 자세 분류
시스템에서 인식하는 8가지 자세:

| ID | 자세명 | 설명 |
|----|--------|------|
| 0 | 바른 자세 | 올바른 앉은 자세 |
| 1 | 거북목 자세 | 목이 앞으로 나온 자세 |
| 2 | 목 숙이기 | 목을 아래로 숙인 자세 |
| 3 | 앞으로 당겨 기대기 | 몸을 앞으로 기울인 자세 |
| 4 | 오른쪽으로 기대기 | 몸이 오른쪽으로 기운 자세 |
| 5 | 왼쪽으로 기대기 | 몸이 왼쪽으로 기운 자세 |
| 6 | 오른쪽 다리 꼭기 | 오른쪽 다리를 꼰 자세 |
| 7 | 왼쪽 다리 꼭기 | 왼쪽 다리를 꼰 자세 |

---

## API 엔드포인트

### 1. API 상태 확인

**GET** `/`

API 서버의 상태를 확인합니다.

#### 응답
```json
{
    "message": "자세 인식 통계 API",
    "version": "1.0.0",
    "status": "running",
    "timestamp": "2024-01-15T10:30:00.123456"
}
```

### 2. 헬스 체크

**GET** `/health`

서버 및 데이터베이스 연결 상태를 확인합니다.

#### 응답
```json
{
    "status": "healthy",
    "database": "connected",
    "total_records": 1524,
    "timestamp": "2024-01-15T10:30:00.123456"
}
```

### 3. 자세별 시간 통계

**GET** `/statistics/postures`

각 자세별 총 시간 및 세션 통계를 조회합니다.

#### 쿼리 파라미터
| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|----------|------|------|------|------|
| start_date | string | 선택 | 시작 날짜 (YYYY-MM-DD) | 2024-01-01 |
| end_date | string | 선택 | 종료 날짜 (YYYY-MM-DD) | 2024-01-15 |
| device_id | string | 선택 | 디바이스 ID | test_device_001 |

#### 요청 예시
```http
GET /statistics/postures?start_date=2024-01-01&end_date=2024-01-15&device_id=test_device_001
```

#### 응답
```json
[
    {
        "posture_id": 0,
        "posture_name": "바른 자세",
        "total_duration_minutes": 125.45,
        "session_count": 15,
        "average_session_duration": 8.36,
        "percentage": 45.2,
        "first_detected": "2024-01-01T09:00:00",
        "last_detected": "2024-01-15T17:30:00"
    },
    {
        "posture_id": 1,
        "posture_name": "거북목 자세",
        "total_duration_minutes": 68.22,
        "session_count": 22,
        "average_session_duration": 3.1,
        "percentage": 24.6,
        "first_detected": "2024-01-01T10:15:00",
        "last_detected": "2024-01-15T16:45:00"
    }
]
```

### 4. 일일 통계

**GET** `/statistics/daily/{date}`

특정 날짜의 자세 통계를 조회합니다.

#### 경로 파라미터
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| date | string | 필수 | 조회할 날짜 (YYYY-MM-DD) |

#### 쿼리 파라미터
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| device_id | string | 선택 | 디바이스 ID |

#### 요청 예시
```http
GET /statistics/daily/2024-01-15?device_id=test_device_001
```

#### 응답
```json
{
    "date": "2024-01-15",
    "total_time_minutes": 480.5,
    "posture_breakdown": [
        {
            "posture_id": 0,
            "posture_name": "바른 자세",
            "total_duration_minutes": 216.8,
            "session_count": 8,
            "average_session_duration": 27.1,
            "percentage": 45.1,
            "first_detected": "2024-01-15T09:00:00",
            "last_detected": "2024-01-15T17:30:00"
        }
    ],
    "most_common_posture": "바른 자세",
    "worst_posture_duration": 85.3
}
```

### 5. 자세 세션 목록

**GET** `/statistics/sessions`

자세 세션 목록을 조회합니다. 각 세션은 연속된 동일한 자세의 시간 구간을 의미합니다.

#### 쿼리 파라미터
| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|----------|------|------|------|-------|
| start_date | string | 선택 | 시작 날짜 (YYYY-MM-DD) | - |
| end_date | string | 선택 | 종료 날짜 (YYYY-MM-DD) | - |
| device_id | string | 선택 | 디바이스 ID | - |
| limit | integer | 선택 | 최대 반환 세션 수 | 100 |

#### 요청 예시
```http
GET /statistics/sessions?start_date=2024-01-15&limit=50
```

#### 응답
```json
[
    {
        "session_id": 1,
        "posture_id": 0,
        "posture_name": "바른 자세",
        "start_time": "2024-01-15T09:00:00",
        "end_time": "2024-01-15T09:25:30",
        "duration_minutes": 25.5,
        "confidence": 0.95
    },
    {
        "session_id": 2,
        "posture_id": 1,
        "posture_name": "거북목 자세",
        "start_time": "2024-01-15T09:25:30",
        "end_time": "2024-01-15T09:28:15",
        "duration_minutes": 2.75,
        "confidence": 0.87
    }
]
```

### 6. 통계 요약

**GET** `/statistics/summary`

지정된 기간의 통계 요약 정보를 제공합니다.

#### 쿼리 파라미터
| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|----------|------|------|------|-------|
| days | integer | 선택 | 최근 며칠간의 데이터 | 7 |
| device_id | string | 선택 | 디바이스 ID | - |

#### 요청 예시
```http
GET /statistics/summary?days=30&device_id=test_device_001
```

#### 응답
```json
{
    "total_monitoring_time": 2400.5,
    "total_sessions": 145,
    "average_session_duration": 16.55,
    "good_posture_percentage": 42.3,
    "most_problematic_posture": "거북목 자세",
    "data_period": "2023-12-16 ~ 2024-01-15"
}
```

### 7. 오늘의 자세 점수

**GET** `/statistics/score/today`

오늘의 자세 점수를 100점 만점으로 계산하여 반환합니다.

#### 쿼리 파라미터
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| device_id | string | 선택 | 디바이스 ID |

#### 점수 계산 방식
- **바른 자세 점수** (60점): 바른 자세 비율에 따라 배점
- **나쁜 자세 감점** (최대 -30점): 각 나쁜 자세의 시간과 심각도에 따라 감점
- **세션 안정성** (20점): 자세 변경 빈도의 적절성 평가

#### 요청 예시
```http
GET /statistics/score/today?device_id=test_device_001
```

#### 응답
```json
{
    "date": "2024-01-15",
    "total_score": 78,
    "good_posture_score": 45,
    "bad_posture_penalty": 12,
    "session_stability_score": 15,
    "monitoring_time_minutes": 480.5,
    "good_posture_percentage": 75.0,
    "worst_posture": "거북목 자세",
    "worst_posture_duration": 85.3,
    "grade": "B+",
    "feedback": "👍 좋은 자세! 바른 자세를 조금 더 유지해보세요."
}
```

### 8. 특정 날짜 자세 점수

**GET** `/statistics/score/{date}`

특정 날짜의 자세 점수를 조회합니다.

#### 경로 파라미터
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| date | string | 필수 | 조회할 날짜 (YYYY-MM-DD) |

#### 쿼리 파라미터
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| device_id | string | 선택 | 디바이스 ID |

#### 요청 예시
```http
GET /statistics/score/2024-01-15?device_id=test_device_001
```

#### 응답
```json
{
    "date": "2024-01-15",
    "total_score": 85,
    "good_posture_score": 52,
    "bad_posture_penalty": 8,
    "session_stability_score": 18,
    "monitoring_time_minutes": 420.0,
    "good_posture_percentage": 86.7,
    "worst_posture": "목 숙이기",
    "worst_posture_duration": 25.5,
    "grade": "A",
    "feedback": "😊 훌륭한 자세! 조금만 더 신경쓰면 완벽해요!"
}
```

### 9. 데이터 초기화

**DELETE** `/data/reset`

⚠️ **주의**: 모든 예측 데이터를 삭제합니다. 복구 불가능!

#### 쿼리 파라미터
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| confirm | boolean | 필수 | 삭제 확인 (반드시 true) |

#### 요청 예시
```http
DELETE /data/reset?confirm=true
```

#### 응답
```json
{
    "success": true,
    "message": "성공적으로 1524개 레코드를 삭제했습니다.",
    "deleted_records": 1524,
    "reset_timestamp": "2024-01-15T16:30:00.123456"
}
```

#### 오류 응답 (confirm=false인 경우)
```json
{
    "detail": "데이터 삭제를 위해 confirm=true 파라미터가 필요합니다"
}
```

### 10. 자세 라벨 목록

**GET** `/postures`

시스템에서 사용하는 자세 분류 라벨 목록을 조회합니다.

#### 응답
```json
{
    "postures": [
        {"id": 0, "name": "바른 자세"},
        {"id": 1, "name": "거북목 자세"},
        {"id": 2, "name": "목 숙이기"},
        {"id": 3, "name": "앞으로 당겨 기대기"},
        {"id": 4, "name": "오른쪽으로 기대기"},
        {"id": 5, "name": "왼쪽으로 기대기"},
        {"id": 6, "name": "오른쪽 다리 꼭기"},
        {"id": 7, "name": "왼쪽 다리 꼭기"}
    ],
    "total_postures": 8
}
```

---

## 오류 응답

### HTTP 상태 코드
- **200**: 성공
- **404**: 데이터를 찾을 수 없음
- **422**: 요청 파라미터 오류
- **500**: 서버 내부 오류

### 오류 응답 형식
```json
{
    "detail": "No data found for date: 2024-01-01"
}
```

---

## 사용 예시

### Python (requests)
```python
import requests

# 오늘의 자세 점수 조회
response = requests.get('http://localhost:8766/statistics/score/today')
score = response.json()
print(f"오늘의 자세 점수: {score['total_score']}점 ({score['grade']})")
print(f"피드백: {score['feedback']}")

# 자세별 통계 조회
response = requests.get(
    'http://localhost:8766/statistics/postures',
    params={
        'start_date': '2024-01-01',
        'end_date': '2024-01-15',
        'device_id': 'test_device_001'
    }
)
stats = response.json()

# 데이터 초기화 (주의!)
response = requests.delete(
    'http://localhost:8766/data/reset',
    params={'confirm': True}
)
reset_result = response.json()
print(f"삭제된 레코드: {reset_result['deleted_records']}개")
```

### JavaScript (fetch)
```javascript
// 오늘의 자세 점수 조회
fetch('http://localhost:8766/statistics/score/today')
    .then(response => response.json())
    .then(data => {
        console.log(`오늘의 점수: ${data.total_score}점 (${data.grade})`);
        console.log(`바른 자세 비율: ${data.good_posture_percentage}%`);
        console.log(`피드백: ${data.feedback}`);
        
        // 점수에 따른 UI 업데이트
        updateScoreDisplay(data.total_score, data.grade, data.feedback);
    });

// 특정 날짜 점수 조회
fetch('http://localhost:8766/statistics/score/2024-01-15')
    .then(response => response.json())
    .then(data => {
        displayScoreHistory(data);
    });

// 통계 요약 조회
fetch('http://localhost:8766/statistics/summary?days=7')
    .then(response => response.json())
    .then(data => {
        console.log('Good posture percentage:', data.good_posture_percentage);
        console.log('Most problematic posture:', data.most_problematic_posture);
    });

// 자세 세션 목록 조회
fetch('http://localhost:8766/statistics/sessions?limit=20')
    .then(response => response.json())
    .then(sessions => {
        sessions.forEach(session => {
            console.log(`${session.posture_name}: ${session.duration_minutes}분`);
        });
    });
```

### cURL
```bash
# 헬스 체크
curl http://localhost:8766/health

# 오늘의 자세 점수
curl http://localhost:8766/statistics/score/today

# 특정 날짜 자세 점수
curl http://localhost:8766/statistics/score/2024-01-15

# 자세별 통계 (특정 기간)
curl "http://localhost:8766/statistics/postures?start_date=2024-01-01&end_date=2024-01-15"

# 일일 통계
curl http://localhost:8766/statistics/daily/2024-01-15

# 통계 요약 (최근 30일)
curl "http://localhost:8766/statistics/summary?days=30"

# 데이터 초기화 (주의!)
curl -X DELETE "http://localhost:8766/data/reset?confirm=true"
```

---

## 데이터 모델

### PostureTimeStats
```json
{
    "posture_id": "integer (자세 ID)",
    "posture_name": "string (자세명)",
    "total_duration_minutes": "float (총 지속시간, 분)",
    "session_count": "integer (세션 수)",
    "average_session_duration": "float (평균 세션 지속시간, 분)",
    "percentage": "float (전체 시간 대비 비율, %)",
    "first_detected": "string (첫 감지 시간, ISO format)",
    "last_detected": "string (마지막 감지 시간, ISO format)"
}
```

### PostureSession
```json
{
    "session_id": "integer (세션 ID)",
    "posture_id": "integer (자세 ID)",
    "posture_name": "string (자세명)",
    "start_time": "string (시작 시간, ISO format)",
    "end_time": "string (종료 시간, ISO format)",
    "duration_minutes": "float (지속시간, 분)",
    "confidence": "float (평균 신뢰도, 0-1)"
}
```

### PostureScore
```json
{
    "date": "string (날짜, YYYY-MM-DD)",
    "total_score": "integer (총 점수, 0-100)",
    "good_posture_score": "integer (바른 자세 점수, 0-60)",
    "bad_posture_penalty": "integer (나쁜 자세 감점, 0-30)",
    "session_stability_score": "integer (세션 안정성 점수, 0-20)",
    "monitoring_time_minutes": "float (총 모니터링 시간, 분)",
    "good_posture_percentage": "float (바른 자세 비율, %)",
    "worst_posture": "string (가장 문제가 되는 자세명)",
    "worst_posture_duration": "float (가장 문제 자세 지속시간, 분)",
    "grade": "string (등급, A+/A/B+/B/C+/C/D)",
    "feedback": "string (피드백 메시지)"
}
```

### DataResetResponse
```json
{
    "success": "boolean (성공 여부)",
    "message": "string (결과 메시지)",
    "deleted_records": "integer (삭제된 레코드 수)",
    "reset_timestamp": "string (초기화 시간, ISO format)"
}
```

### 자세 점수 등급 기준
| 점수 범위 | 등급 | 설명 |
|-----------|------|------|
| 90-100점 | A+ | 🌟 완벽한 자세 |
| 80-89점 | A | 😊 훌륭한 자세 |
| 70-79점 | B+ | 👍 좋은 자세 |
| 60-69점 | B | 😐 보통 자세 |
| 50-59점 | C+ | 😟 자세 개선 필요 |
| 40-49점 | C | 🚨 자세에 주의 필요 |
| 0-39점 | D | ⚠️ 자세가 매우 좋지 않음 |

---

## 통합 서버 실행

### 단일 서버 실행 (WebSocket + REST API)
```bash
# 통합 서버 실행
python integrated_server.py

# 개별 서버 실행
python websocket_server.py    # WebSocket 서버 (포트 8765)
python statistics_api.py      # REST API 서버 (포트 8766)
```

### 서버 접속 정보
- **WebSocket 서버**: `ws://localhost:8765` (실시간 자세 인식)
- **REST API 서버**: `http://localhost:8766` (통계 조회)
- **API 문서**: `http://localhost:8766/docs` (Swagger UI)
- **API 스키마**: `http://localhost:8766/redoc` (ReDoc)

---

## 주의사항

1. **시간 계산**: 자세 지속 시간은 연속된 동일한 자세 예측 결과를 기반으로 계산됩니다.
2. **세션 정의**: 자세가 변경되면 이전 세션이 종료되고 새로운 세션이 시작됩니다.
3. **데이터 정확성**: 통계는 데이터베이스에 저장된 예측 결과를 기반으로 하므로, WebSocket 연결이 끊어진 구간은 계산에서 제외됩니다.
4. **타임존**: 모든 시간은 서버의 로컬 타임존을 기준으로 합니다.
5. **성능**: 대량의 데이터 조회 시 성능을 위해 적절한 날짜 범위를 지정하는 것을 권장합니다.