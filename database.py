import sqlite3
import asyncio
from datetime import datetime
import logging
from config import config

# 로거 설정
logger = logging.getLogger(__name__)

class PostureDatabase:
    def __init__(self, db_path=None):
        self.db_path = db_path or config.DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """데이터베이스와 테이블 초기화"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 자세 판별 결과 저장 테이블
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS posture_predictions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id TEXT NOT NULL,
                        device_id TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        predicted_posture INTEGER NOT NULL,
                        confidence REAL NOT NULL,
                        imu_data TEXT,
                        fsr_data TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 클라이언트 연결 로그 테이블
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS client_connections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id TEXT NOT NULL,
                        device_id TEXT,
                        connect_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                        disconnect_time DATETIME,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                ''')
                
                # 자세 분류 레이블 테이블 (참조용)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS posture_labels (
                        posture_id INTEGER PRIMARY KEY,
                        label_ko TEXT NOT NULL,
                        label_en TEXT NOT NULL,
                        description TEXT
                    )
                ''')
                
                # 기본 자세 레이블 데이터 삽입
                posture_labels = [
                    (0, "정자세", "Normal Posture", "올바른 앉은 자세"),
                    (1, "오른쪽 다리꼬기", "Right Leg Cross", "오른쪽 다리를 왼쪽 다리 위에 올린 자세"),
                    (2, "왼쪽 다리꼬기", "Left Leg Cross", "왼쪽 다리를 오른쪽 다리 위에 올린 자세"),
                    (3, "등 기대고 엉덩이 앞으로", "Slouching", "등받이에 기대고 엉덩이가 앞으로 나온 자세"),
                    (4, "거북목(폰 보면서 목 숙이기)", "Turtle Neck (Phone)", "폰을 보면서 목을 아래로 숙인 자세"),
                    (5, "오른쪽 팔걸이", "Right Armrest", "오른쪽 팔걸이에 팔을 올린 자세"),
                    (6, "왼쪽 팔걸이", "Left Armrest", "왼쪽 팔걸이에 팔을 올린 자세"),
                    (7, "목 앞으로 나오는(컴퓨터 할 때)", "Forward Head (Computer)", "컴퓨터 작업 시 목이 앞으로 나온 자세")
                ]
                
                cursor.executemany('''
                    INSERT OR IGNORE INTO posture_labels 
                    (posture_id, label_ko, label_en, description) 
                    VALUES (?, ?, ?, ?)
                ''', posture_labels)
                
                conn.commit()
                logger.info("데이터베이스 초기화 완료")
                
        except Exception as e:
            logger.error(f"데이터베이스 초기화 오류: {e}")
            raise
    
    async def save_prediction(self, client_id, device_id, posture, confidence, imu_data=None, fsr_data=None):
        """자세 예측 결과를 데이터베이스에 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO posture_predictions 
                    (client_id, device_id, predicted_posture, confidence, imu_data, fsr_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (client_id, device_id, posture, confidence, str(imu_data), str(fsr_data)))
                conn.commit()
                
                prediction_id = cursor.lastrowid
                logger.info(f"예측 결과 저장 완료 - ID: {prediction_id}, 자세: {posture}, 신뢰도: {confidence:.3f}")
                return prediction_id
                
        except Exception as e:
            logger.error(f"예측 결과 저장 오류: {e}")
            raise
    
    async def log_client_connection(self, client_id, device_id=None):
        """클라이언트 연결 로그"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO client_connections (client_id, device_id)
                    VALUES (?, ?)
                ''', (client_id, device_id))
                conn.commit()
                logger.info(f"클라이언트 연결 기록 - ID: {client_id}")
                
        except Exception as e:
            logger.error(f"클라이언트 연결 로그 오류: {e}")
    
    async def log_client_disconnection(self, client_id):
        """클라이언트 연결 해제 로그"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE client_connections 
                    SET disconnect_time = CURRENT_TIMESTAMP, is_active = FALSE
                    WHERE client_id = ? AND is_active = TRUE
                ''', (client_id,))
                conn.commit()
                logger.info(f"클라이언트 연결 해제 기록 - ID: {client_id}")
                
        except Exception as e:
            logger.error(f"클라이언트 연결 해제 로그 오류: {e}")
    
    def get_posture_stats(self, limit=100):
        """최근 자세 통계 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT pp.predicted_posture, pl.label_ko, COUNT(*) as count,
                           AVG(pp.confidence) as avg_confidence,
                           MAX(pp.timestamp) as last_detected
                    FROM posture_predictions pp
                    JOIN posture_labels pl ON pp.predicted_posture = pl.posture_id
                    WHERE pp.timestamp >= datetime('now', '-1 day')
                    GROUP BY pp.predicted_posture, pl.label_ko
                    ORDER BY count DESC
                    LIMIT ?
                ''', (limit,))
                
                results = cursor.fetchall()
                return [
                    {
                        'posture_id': row[0],
                        'label': row[1],
                        'count': row[2],
                        'avg_confidence': round(row[3], 3),
                        'last_detected': row[4]
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"자세 통계 조회 오류: {e}")
            return []

# 전역 데이터베이스 인스턴스
db = PostureDatabase()