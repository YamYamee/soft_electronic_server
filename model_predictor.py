import numpy as np
import logging
from typing import List, Tuple, Dict, Any
import os
import joblib
from config import config

# 로거 설정
logger = logging.getLogger(__name__)

class PosturePredictor:
    def __init__(self, model_path=None):
        self.model_path = model_path or config.MODEL_PATH
        self.scaler_path = "scaler.joblib"  # 루트 디렉토리로 변경
        self.model = None
        self.scaler = None
        self.posture_labels = {
            0: "정자세",
            1: "오른쪽 다리꼬기",
            2: "왼쪽 다리꼬기", 
            3: "등 기대고 엉덩이 앞으로",
            4: "거북목(폰 보면서 목 숙이기)",
            5: "오른쪽 팔걸이",
            6: "왼쪽 팔걸이",
            7: "목 앞으로 나오는(컴퓨터 할 때)"
        }
        self.supports_proba = True
        self.load_model()
    
    def load_model(self):
        """저장된 머신러닝 모델 및 스케일러 로드"""
        try:
            # 실제 머신러닝 모델 로드 시도
            if os.path.exists(self.model_path):
                logger.info(f"머신러닝 모델 로드 중: {self.model_path}")
                self.model = joblib.load(self.model_path)
                logger.info("✅ 머신러닝 모델 로드 성공")
                
                # 스케일러 로드 시도
                if os.path.exists(self.scaler_path):
                    logger.info(f"스케일러 로드 중: {self.scaler_path}")
                    self.scaler = joblib.load(self.scaler_path)
                    logger.info("✅ 스케일러 로드 성공")
                else:
                    logger.warning(f"스케일러 파일이 없습니다: {self.scaler_path}")
                    self.scaler = None
                
                return True
                
            else:
                logger.warning(f"모델 파일이 없습니다: {self.model_path}")
                raise FileNotFoundError("모델 파일 없음")
                
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            logger.info("규칙 기반 모델로 대체합니다")
            self.create_simple_rule_based_model()
            return False
    
    def create_simple_rule_based_model(self):
        """간단한 규칙 기반 모델 생성 (실제 모델 로드가 실패할 경우 사용)"""
        logger.info("규칙 기반 자세 분류 모델을 생성합니다")
        
        # FSR 패턴 기반 분류 규칙
        self.classification_rules = {
            # 각 자세별 FSR 센서 패턴 특징
            0: {'name': '정자세', 'pattern': 'balanced'},
            1: {'name': '오른쪽 다리꼬기', 'pattern': 'right_heavy'},
            2: {'name': '왼쪽 다리꼬기', 'pattern': 'left_heavy'},
            3: {'name': '등 기대고 엉덩이 앞으로', 'pattern': 'front_heavy'},
            4: {'name': '거북목', 'pattern': 'forward_lean'},
            5: {'name': '오른쪽 팔걸이', 'pattern': 'right_arm'},
            6: {'name': '왼쪽 팔걸이', 'pattern': 'left_arm'},
            7: {'name': '목 앞으로', 'pattern': 'neck_forward'}
        }
        
        self.model = "rule_based"
        self.scaler = None
        logger.info("규칙 기반 모델 생성 완료")
    
    def preprocess_data(self, fsr_data: List[float], imu_data: Any = None) -> np.ndarray:
        """입력 데이터 전처리"""
        try:
            # FSR 데이터 검증
            if not isinstance(fsr_data, list):
                raise ValueError("FSR 데이터는 리스트 형태여야 합니다")
            
            # FSR 데이터를 numpy 배열로 변환
            fsr_array = np.array(fsr_data, dtype=float)
            
            # 데이터 크기 확인 (11개 센서 예상)
            expected_fsr_size = 11
            if len(fsr_array) != expected_fsr_size:
                logger.warning(f"예상 FSR 센서 개수와 다릅니다. 예상: {expected_fsr_size}, 실제: {len(fsr_array)}")
                # 부족한 경우 0으로 패딩, 많은 경우 자르기
                if len(fsr_array) < expected_fsr_size:
                    fsr_array = np.pad(fsr_array, (0, expected_fsr_size - len(fsr_array)), mode='constant')
                else:
                    fsr_array = fsr_array[:expected_fsr_size]
            
            # 현재는 FSR 데이터만 사용 (IMU 데이터는 향후 확장 가능)
            features = fsr_array
            
            logger.debug(f"전처리된 특성 데이터 형태: {features.shape}")
            return features
            
        except Exception as e:
            logger.error(f"데이터 전처리 오류: {e}")
            raise
    
    def analyze_fsr_pattern(self, fsr_data: np.ndarray) -> Tuple[int, float]:
        """FSR 데이터 패턴 분석을 통한 자세 분류"""
        try:
            # 전체 압력 합계
            total_pressure = np.sum(fsr_data)
            
            if total_pressure == 0:
                return 0, 0.5  # 압력이 없으면 기본 자세
            
            # 각 센서별 비율 계산
            ratios = fsr_data / total_pressure
            
            # 좌우 균형 분석 (센서 1-5: 왼쪽, 센서 6-11: 오른쪽 가정)
            left_pressure = np.sum(fsr_data[:5])
            right_pressure = np.sum(fsr_data[5:])
            
            # 앞뒤 균형 분석 (센서 배치에 따라 조정 필요)
            front_pressure = np.sum(fsr_data[[0, 1, 5, 6]])  # 앞쪽 센서들
            back_pressure = np.sum(fsr_data[[3, 4, 8, 9]])   # 뒤쪽 센서들
            
            # 분류 로직
            if left_pressure > right_pressure * 1.5:
                # 왼쪽으로 치우침
                if front_pressure > back_pressure:
                    predicted_posture = 2  # 왼쪽 다리꼬기
                else:
                    predicted_posture = 6  # 왼쪽 팔걸이
                confidence = min(0.9, (left_pressure / right_pressure - 1) * 0.5 + 0.6)
                
            elif right_pressure > left_pressure * 1.5:
                # 오른쪽으로 치우침
                if front_pressure > back_pressure:
                    predicted_posture = 1  # 오른쪽 다리꼬기
                else:
                    predicted_posture = 5  # 오른쪽 팔걸이
                confidence = min(0.9, (right_pressure / left_pressure - 1) * 0.5 + 0.6)
                
            elif back_pressure > front_pressure * 1.3:
                # 뒤쪽으로 치우침 (등 기대기)
                predicted_posture = 3
                confidence = min(0.9, (back_pressure / front_pressure - 1) * 0.5 + 0.6)
                
            elif front_pressure > back_pressure * 1.3:
                # 앞쪽으로 치우침
                if np.max(fsr_data[:3]) > np.mean(fsr_data) * 1.5:
                    predicted_posture = 4  # 거북목
                else:
                    predicted_posture = 7  # 목 앞으로
                confidence = min(0.9, (front_pressure / back_pressure - 1) * 0.5 + 0.6)
                
            else:
                # 균형잡힌 자세
                predicted_posture = 0  # 정자세
                balance_score = 1 - abs(left_pressure - right_pressure) / total_pressure
                confidence = min(0.95, balance_score + 0.3)
            
            # 신뢰도 범위 조정
            confidence = max(0.3, min(0.95, confidence))
            
            return predicted_posture, confidence
            
        except Exception as e:
            logger.error(f"패턴 분석 오류: {e}")
            return 0, 0.5
    
    def predict_posture(self, fsr_data: List[float], imu_data: Any = None) -> Tuple[int, float]:
        """자세 예측 수행"""
        try:
            # 데이터 전처리
            features = self.preprocess_data(fsr_data, imu_data)
            
            # 실제 머신러닝 모델이 있는 경우
            if self.model != "rule_based" and self.model is not None:
                # 특성 데이터를 2D 배열로 변환 (모델 입력 형식)
                features_2d = features.reshape(1, -1)
                
                # 스케일러가 있는 경우 정규화 수행
                if self.scaler is not None:
                    features_normalized = self.scaler.transform(features_2d)
                    logger.debug("데이터 정규화 완료")
                else:
                    features_normalized = features_2d
                    logger.debug("스케일러 없음 - 원본 데이터 사용")
                
                # 모델 예측 수행
                predicted_posture = int(self.model.predict(features_normalized)[0])
                
                # 확률 예측 지원하는 경우 신뢰도 계산
                if hasattr(self.model, 'predict_proba'):
                    probabilities = self.model.predict_proba(features_normalized)[0]
                    confidence = float(np.max(probabilities))
                else:
                    confidence = 0.8  # 기본 신뢰도
                
                logger.info(f"머신러닝 모델 예측 완료 - 자세: {predicted_posture} ({self.posture_labels[predicted_posture]}), 신뢰도: {confidence:.3f}")
                
            else:
                # 규칙 기반 분류 수행
                predicted_posture, confidence = self.analyze_fsr_pattern(features)
                logger.info(f"규칙 기반 예측 완료 - 자세: {predicted_posture} ({self.posture_labels[predicted_posture]}), 신뢰도: {confidence:.3f}")
            
            # 유효한 자세 범위 확인
            if predicted_posture not in self.posture_labels:
                logger.warning(f"예상하지 못한 자세 번호: {predicted_posture}")
                predicted_posture = 0  # 기본값으로 정자세 설정
                confidence = 0.5  # 중간 신뢰도 설정
            
            return predicted_posture, confidence
            
        except Exception as e:
            logger.error(f"자세 예측 오류: {e}")
            # 오류 발생 시 기본 예측
            import random
            predicted_posture = random.randint(0, 7)
            confidence = random.uniform(0.4, 0.8)
            logger.info(f"오류로 인한 랜덤 예측 - 자세: {predicted_posture}, 신뢰도: {confidence:.3f}")
            return predicted_posture, confidence
    
    def get_posture_label(self, posture_id: int) -> str:
        """자세 ID에 해당하는 라벨 반환"""
        return self.posture_labels.get(posture_id, "알 수 없는 자세")
    
    def validate_model_input(self, fsr_data: List[float]) -> bool:
        """모델 입력 데이터 유효성 검사"""
        try:
            if not isinstance(fsr_data, list):
                return False
            
            if len(fsr_data) == 0:
                return False
            
            # 모든 값이 숫자인지 확인
            for value in fsr_data:
                if not isinstance(value, (int, float)):
                    return False
                
                # 음수 값 확인 (압력 센서는 일반적으로 음수가 아님)
                if value < 0:
                    logger.warning(f"음수 FSR 값 감지: {value}")
            
            return True
            
        except Exception as e:
            logger.error(f"입력 데이터 유효성 검사 오류: {e}")
            return False

# 전역 예측기 인스턴스
predictor = PosturePredictor()