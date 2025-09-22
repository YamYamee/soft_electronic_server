"""
데이터베이스 자세 라벨 업데이트 스크립트
새로운 8가지 자세 분류로 업데이트
"""

import sqlite3
import logging
from config import config

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 새로운 자세 라벨 (업데이트된 8가지)
NEW_POSTURE_LABELS = [
    (0, "바른 자세", "Normal Posture", "올바른 앉은 자세"),
    (1, "거북목 자세", "Turtle Neck", "목이 앞으로 나온 자세"),
    (2, "목 숙이기", "Head Down", "목을 아래로 숙인 자세"),
    (3, "앞으로 당겨 기대기", "Forward Lean", "몸을 앞으로 기울여 기대는 자세"),
    (4, "오른쪽으로 기대기", "Right Lean", "몸이 오른쪽으로 기운 자세"),
    (5, "왼쪽으로 기대기", "Left Lean", "몸이 왼쪽으로 기운 자세"),
    (6, "오른쪽 다리 꼭기", "Right Leg Cross", "오른쪽 다리를 꼰 자세"),
    (7, "왼쪽 다리 꼭기", "Left Leg Cross", "왼쪽 다리를 꼰 자세")
]

def update_posture_labels():
    """데이터베이스의 자세 라벨을 새로운 8가지로 업데이트"""
    try:
        with sqlite3.connect(config.DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # 기존 라벨 삭제
            logger.info("기존 자세 라벨 삭제 중...")
            cursor.execute("DELETE FROM posture_labels")
            
            # 새로운 라벨 삽입
            logger.info("새로운 자세 라벨 삽입 중...")
            cursor.executemany('''
                INSERT INTO posture_labels 
                (posture_id, label_ko, label_en, description) 
                VALUES (?, ?, ?, ?)
            ''', NEW_POSTURE_LABELS)
            
            conn.commit()
            
            # 업데이트 확인
            cursor.execute("SELECT COUNT(*) FROM posture_labels")
            count = cursor.fetchone()[0]
            
            logger.info(f"자세 라벨 업데이트 완료: {count}개 라벨")
            
            # 업데이트된 라벨 출력
            cursor.execute("SELECT posture_id, label_ko, label_en FROM posture_labels ORDER BY posture_id")
            labels = cursor.fetchall()
            
            logger.info("업데이트된 자세 라벨:")
            for posture_id, label_ko, label_en in labels:
                logger.info(f"  {posture_id}: {label_ko} ({label_en})")
            
            return True
            
    except Exception as e:
        logger.error(f"자세 라벨 업데이트 오류: {e}")
        return False

def verify_database_schema():
    """데이터베이스 스키마 확인"""
    try:
        with sqlite3.connect(config.DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # 테이블 존재 확인
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='posture_labels'
            """)
            
            if not cursor.fetchone():
                logger.error("posture_labels 테이블이 존재하지 않습니다.")
                return False
            
            # 테이블 스키마 확인
            cursor.execute("PRAGMA table_info(posture_labels)")
            columns = cursor.fetchall()
            
            expected_columns = ['posture_id', 'label_ko', 'label_en', 'description']
            actual_columns = [col[1] for col in columns]
            
            for col in expected_columns:
                if col not in actual_columns:
                    logger.error(f"필요한 컬럼이 없습니다: {col}")
                    return False
            
            logger.info("데이터베이스 스키마 확인 완료")
            return True
            
    except Exception as e:
        logger.error(f"데이터베이스 스키마 확인 오류: {e}")
        return False

def main():
    """메인 업데이트 프로세스"""
    logger.info("=== 자세 라벨 업데이트 시작 ===")
    
    # 스키마 확인
    if not verify_database_schema():
        logger.error("데이터베이스 스키마 확인 실패")
        return False
    
    # 자세 라벨 업데이트
    if update_posture_labels():
        logger.info("자세 라벨 업데이트 성공!")
        return True
    else:
        logger.error("자세 라벨 업데이트 실패!")
        return False

if __name__ == "__main__":
    main()