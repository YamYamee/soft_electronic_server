import numpy as np
import logging
from typing import List, Tuple, Dict, Any, Optional
import os
import random
import joblib
from datetime import datetime
from config import config
from database import DatabaseManager

# 로거 설정
logger = logging.getLogger(__name__)

class EnsemblePosturePredictor:
    def __init__(self, model_path=None):
        self.model_path = model_path or config.MODEL_PATH
        self.models = {}
        self.scaler = None
        self.posture_labels = {
            0: "바른 자세",
            1: "거북목 자세",
            2: "목 숙이기", 
            3: "앞으로 당겨 기대기",
            4: "오른쪽으로 기대기",
            5: "왼쪽으로 기대기",
            6: "오른쪽 다리 꼬기",
            7: "왼쪽 다리 꼬기"
        }
        self.supports_proba = True
        self.db_manager = DatabaseManager()
        self.load_ensemble_models()
        
        # 모델별 가중치 (성능에 따라 조정 가능)
        self.model_weights = {
            'lr': 0.3,    # Logistic Regression
            'rf': 0.35,   # Random Forest (일반적으로 성능이 좋음)
            'dt': 0.2,    # Decision Tree
            'kn': 0.15    # K-Nearest Neighbors
        }
        
        # 예측 로그를 위한 DB 테이블 생성
        self.create_prediction_log_table()
    
    def create_prediction_log_table(self):
        """예측 로그를 저장할 테이블 생성"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS prediction_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        client_id TEXT,
                        device_id TEXT,
                        fsr_data TEXT NOT NULL,
                        imu_data TEXT,
                        raw_fsr_values TEXT,
                        preprocessed_data TEXT,
                        
                        -- 개별 모델 예측 결과
                        lr_prediction INTEGER,
                        lr_confidence REAL,
                        rf_prediction INTEGER,
                        rf_confidence REAL,
                        dt_prediction INTEGER,
                        dt_confidence REAL,
                        kn_prediction INTEGER,
                        kn_confidence REAL,
                        
                        -- 앙상블 결과
                        ensemble_prediction INTEGER NOT NULL,
                        ensemble_confidence REAL NOT NULL,
                        voting_scores TEXT,
                        
                        -- 메타 정보
                        models_used TEXT,
                        prediction_method TEXT DEFAULT 'ensemble',
                        processing_time_ms REAL
                    )
                ''')
                conn.commit()
                logger.info("예측 로그 테이블 생성 완료")
        except Exception as e:
            logger.error(f"예측 로그 테이블 생성 오류: {e}")

    def load_ensemble_models(self):
        """여러 ML 모델들을 로드하여 앙상블 구성"""
        ml_dir = os.path.join(os.path.dirname(__file__), 'ML')
        model_files = {
            'lr': 'model_lr.joblib',
            'rf': 'model_rf.joblib', 
            'dt': 'model_dt.joblib',
            'kn': 'model_kn.joblib'
        }
        
        scaler_path = os.path.join(ml_dir, 'scaler.joblib')
        
        logger.info("앙상블 모델 로딩 시작...")
        
        # 스케일러 로드
        try:
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
                logger.info("✅ 스케일러 로드 완료")
            else:
                logger.warning("⚠️ 스케일러 파일을 찾을 수 없습니다")
        except Exception as e:
            logger.error(f"스케일러 로드 오류: {e}")
        
        # 각 모델 로드
        loaded_models = 0
        for model_name, model_file in model_files.items():
            model_path = os.path.join(ml_dir, model_file)
            try:
                if os.path.exists(model_path):
                    model = joblib.load(model_path)
                    self.models[model_name] = model
                    loaded_models += 1
                    logger.info(f"✅ {model_name.upper()} 모델 로드 완료")
                else:
                    logger.warning(f"⚠️ {model_name.upper()} 모델 파일을 찾을 수 없습니다: {model_path}")
            except Exception as e:
                logger.error(f"❌ {model_name.upper()} 모델 로드 오류: {e}")
        
        if loaded_models == 0:
            logger.warning("사용 가능한 ML 모델이 없어 규칙 기반 모델로 대체합니다")
            self.create_simple_rule_based_model()
        else:
            logger.info(f"🎯 앙상블 구성 완료: {loaded_models}개 모델 로드됨")
            
        return loaded_models > 0

    def create_simple_rule_based_model(self):
        """간단한 규칙 기반 모델 생성 (ML 모델 로드가 실패할 경우 사용)"""
        logger.info("규칙 기반 자세 분류 모델을 생성합니다")
        
        # FSR 패턴 기반 분류 규칙
        self.classification_rules = {
            # 각 자세별 FSR 센서 패턴 특징
            0: {'name': '바른 자세', 'pattern': 'balanced'},
            1: {'name': '거북목 자세', 'pattern': 'neck_forward'},
            2: {'name': '목 숙이기', 'pattern': 'head_down'},
            3: {'name': '앞으로 당겨 기대기', 'pattern': 'front_heavy'},
            4: {'name': '오른쪽으로 기대기', 'pattern': 'right_lean'},
            5: {'name': '왼쪽으로 기대기', 'pattern': 'left_lean'},
            6: {'name': '오른쪽 다리 꼬기', 'pattern': 'right_leg_cross'},
            7: {'name': '왼쪽 다리 꼬기', 'pattern': 'left_leg_cross'}
        }
        
        self.models = {"rule_based": "rule_based"}
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
            
            # 분류 로직 (새로운 자세 분류에 맞게 조정)
            if left_pressure > right_pressure * 1.5:
                # 왼쪽으로 치우침
                if front_pressure > back_pressure:
                    predicted_posture = 7  # 왼쪽 다리 꼭기
                else:
                    predicted_posture = 5  # 왼쪽으로 기대기
                confidence = min(0.9, (left_pressure / right_pressure - 1) * 0.5 + 0.6)
                
            elif right_pressure > left_pressure * 1.5:
                # 오른쪽으로 치우침
                if front_pressure > back_pressure:
                    predicted_posture = 6  # 오른쪽 다리 꼭기
                else:
                    predicted_posture = 4  # 오른쪽으로 기대기
                confidence = min(0.9, (right_pressure / left_pressure - 1) * 0.5 + 0.6)
                
            elif front_pressure > back_pressure * 1.3:
                # 앞쪽으로 치우침
                if np.max(fsr_data[:3]) > np.mean(fsr_data) * 1.5:
                    predicted_posture = 2  # 목 숙이기
                elif np.mean(fsr_data[:5]) > np.mean(fsr_data[5:]) * 1.2:
                    predicted_posture = 1  # 거북목 자세
                else:
                    predicted_posture = 3  # 앞으로 당겨 기대기
                confidence = min(0.9, (front_pressure / back_pressure - 1) * 0.5 + 0.6)
                
            else:
                # 균형잡힌 자세
                predicted_posture = 0  # 바른 자세
                balance_score = 1 - abs(left_pressure - right_pressure) / total_pressure
                confidence = min(0.95, balance_score + 0.3)
            
            # 신뢰도 범위 조정
            confidence = max(0.3, min(0.95, confidence))
            
            return predicted_posture, confidence
            
        except Exception as e:
            logger.error(f"패턴 분석 오류: {e}")
            return 0, 0.5
    
    def predict_posture(self, fsr_data: List[float], imu_data: Any = None, 
                       client_id: str = None, device_id: str = None) -> Tuple[int, float]:
        """앙상블 기반 자세 예측 수행"""
        start_time = datetime.now()
        
        try:
            # 데이터 전처리
            features = self.preprocess_data(fsr_data, imu_data)
            
            # ML 모델이 있으면 앙상블 예측, 없으면 규칙 기반
            if len(self.models) > 1 and "rule_based" not in self.models:
                predicted_posture, confidence, prediction_details = self.ensemble_predict(features)
                method = "ensemble"
            else:
                # 규칙 기반 분류 수행
                predicted_posture, confidence = self.analyze_fsr_pattern(features)
                prediction_details = {
                    "rule_based": {"prediction": predicted_posture, "confidence": confidence}
                }
                method = "rule_based"
            
            # 유효한 자세 범위 확인
            if predicted_posture not in self.posture_labels:
                logger.warning(f"예상하지 못한 자세 번호: {predicted_posture}")
                predicted_posture = 0  # 기본값으로 정자세 설정
                confidence = 0.5  # 중간 신뢰도 설정
            
            # 처리 시간 계산
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 예측 로그 저장 (비동기적으로)
            self.log_prediction(
                client_id=client_id,
                device_id=device_id,
                fsr_data=fsr_data,
                imu_data=imu_data,
                features=features,
                prediction_details=prediction_details,
                final_prediction=predicted_posture,
                final_confidence=confidence,
                method=method,
                processing_time=processing_time
            )
            
            logger.info(f"자세 예측 완료 - 자세: {predicted_posture} ({self.posture_labels[predicted_posture]}), "
                       f"신뢰도: {confidence:.3f}, 방법: {method}, 처리시간: {processing_time:.1f}ms")
            
            return predicted_posture, confidence
            
        except Exception as e:
            logger.error(f"자세 예측 오류: {e}")
            # 오류 발생 시 랜덤 예측 (데모 목적)
            predicted_posture = random.randint(0, 7)
            confidence = random.uniform(0.4, 0.8)
            logger.info(f"오류로 인한 랜덤 예측 - 자세: {predicted_posture}, 신뢰도: {confidence:.3f}")
            return predicted_posture, confidence

    def ensemble_predict(self, features: np.ndarray) -> Tuple[int, float, Dict]:
        """앙상블 모델을 사용한 예측"""
        if self.scaler is not None:
            # 데이터 정규화
            features_scaled = self.scaler.transform(features.reshape(1, -1))
        else:
            features_scaled = features.reshape(1, -1)
            logger.warning("스케일러가 없어서 정규화를 수행하지 않습니다")
        
        predictions = {}
        confidences = {}
        voting_scores = np.zeros(8)  # 8개 클래스에 대한 투표
        
        # 각 모델별 예측 수행
        for model_name, model in self.models.items():
            if model_name == "rule_based":
                continue
                
            try:
                # 예측 수행
                pred = model.predict(features_scaled)[0]
                predictions[model_name] = pred
                
                # 신뢰도 계산 (확률 예측이 가능한 경우)
                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba(features_scaled)[0]
                    confidence = np.max(proba)
                    confidences[model_name] = confidence
                    
                    # 가중 투표 (확률 기반)
                    weight = self.model_weights.get(model_name, 1.0)
                    voting_scores += proba * weight
                else:
                    # 단순 투표
                    confidence = 0.7  # 기본 신뢰도
                    confidences[model_name] = confidence
                    weight = self.model_weights.get(model_name, 1.0)
                    voting_scores[pred] += weight
                    
                logger.debug(f"{model_name.upper()} 예측: {pred}, 신뢰도: {confidence:.3f}")
                
            except Exception as e:
                logger.error(f"{model_name.upper()} 모델 예측 오류: {e}")
                continue
        
        if len(predictions) == 0:
            # 모든 모델이 실패한 경우 규칙 기반으로 대체
            logger.warning("모든 ML 모델 예측 실패, 규칙 기반으로 대체")
            pred, conf = self.analyze_fsr_pattern(features)
            return pred, conf, {"rule_based_fallback": {"prediction": pred, "confidence": conf}}
        
        # 최종 예측 결정 (가장 높은 점수)
        final_prediction = np.argmax(voting_scores)
        
        # 앙상블 신뢰도 계산 (정규화된 최대 투표 점수)
        if np.sum(voting_scores) > 0:
            final_confidence = voting_scores[final_prediction] / np.sum(voting_scores)
        else:
            final_confidence = 0.5
        
        # 신뢰도 범위 조정
        final_confidence = max(0.3, min(0.95, final_confidence))
        
        prediction_details = {
            'individual_predictions': predictions,
            'individual_confidences': confidences,
            'voting_scores': voting_scores.tolist(),
            'ensemble_prediction': final_prediction,
            'ensemble_confidence': final_confidence
        }
        
        logger.debug(f"앙상블 예측 완료 - 최종: {final_prediction}, 신뢰도: {final_confidence:.3f}")
        
        return final_prediction, final_confidence, prediction_details
    
    def get_posture_label(self, posture_id: int) -> str:
        """자세 ID에 해당하는 라벨 반환"""
        return self.posture_labels.get(posture_id, "알 수 없는 자세")
    
    def log_prediction(self, client_id: Optional[str], device_id: Optional[str], 
                      fsr_data: List[float], imu_data: Any, features: np.ndarray,
                      prediction_details: Dict, final_prediction: int, final_confidence: float,
                      method: str, processing_time: float):
        """예측 결과를 DB에 로그로 저장"""
        try:
            import json
            
            # 데이터 직렬화
            fsr_json = json.dumps(fsr_data)
            imu_json = json.dumps(imu_data) if imu_data else None
            features_json = json.dumps(features.tolist())
            details_json = json.dumps(prediction_details, default=str)
            models_used = list(self.models.keys())
            models_json = json.dumps(models_used)
            
            # 개별 모델 결과 추출
            individual_preds = prediction_details.get('individual_predictions', {})
            individual_confs = prediction_details.get('individual_confidences', {})
            voting_scores = prediction_details.get('voting_scores', [])
            voting_json = json.dumps(voting_scores) if voting_scores else None
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO prediction_logs (
                        client_id, device_id, fsr_data, imu_data, raw_fsr_values, preprocessed_data,
                        lr_prediction, lr_confidence, rf_prediction, rf_confidence,
                        dt_prediction, dt_confidence, kn_prediction, kn_confidence,
                        ensemble_prediction, ensemble_confidence, voting_scores,
                        models_used, prediction_method, processing_time_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    client_id, device_id, fsr_json, imu_json, fsr_json, features_json,
                    individual_preds.get('lr'), individual_confs.get('lr'),
                    individual_preds.get('rf'), individual_confs.get('rf'),
                    individual_preds.get('dt'), individual_confs.get('dt'),
                    individual_preds.get('kn'), individual_confs.get('kn'),
                    final_prediction, final_confidence, voting_json,
                    models_json, method, processing_time
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"예측 로그 저장 오류: {e}")

    def get_prediction_statistics(self, hours: int = 24) -> Dict:
        """최근 예측 통계 조회"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 최근 예측 통계
                cursor.execute('''
                    SELECT 
                        prediction_method,
                        COUNT(*) as count,
                        AVG(ensemble_confidence) as avg_confidence,
                        AVG(processing_time_ms) as avg_processing_time
                    FROM prediction_logs 
                    WHERE timestamp >= datetime('now', '-{} hours')
                    GROUP BY prediction_method
                '''.format(hours))
                
                stats = {}
                for row in cursor.fetchall():
                    method, count, avg_conf, avg_time = row
                    stats[method] = {
                        'predictions_count': count,
                        'average_confidence': round(avg_conf or 0, 3),
                        'average_processing_time_ms': round(avg_time or 0, 2)
                    }
                
                # 모델별 정확도 (개별 모델 결과)
                cursor.execute('''
                    SELECT 
                        COUNT(CASE WHEN lr_prediction = ensemble_prediction THEN 1 END) * 100.0 / COUNT(*) as lr_agreement,
                        COUNT(CASE WHEN rf_prediction = ensemble_prediction THEN 1 END) * 100.0 / COUNT(*) as rf_agreement,
                        COUNT(CASE WHEN dt_prediction = ensemble_prediction THEN 1 END) * 100.0 / COUNT(*) as dt_agreement,
                        COUNT(CASE WHEN kn_prediction = ensemble_prediction THEN 1 END) * 100.0 / COUNT(*) as kn_agreement
                    FROM prediction_logs 
                    WHERE timestamp >= datetime('now', '-{} hours')
                    AND prediction_method = 'ensemble'
                '''.format(hours))
                
                agreement_row = cursor.fetchone()
                if agreement_row:
                    stats['model_agreement'] = {
                        'lr_agreement_pct': round(agreement_row[0] or 0, 1),
                        'rf_agreement_pct': round(agreement_row[1] or 0, 1),
                        'dt_agreement_pct': round(agreement_row[2] or 0, 1),
                        'kn_agreement_pct': round(agreement_row[3] or 0, 1)
                    }
                
                return stats
                
        except Exception as e:
            logger.error(f"예측 통계 조회 오류: {e}")
            return {}

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

# PosturePredictor 클래스는 이제 EnsemblePosturePredictor로 대체됨
PosturePredictor = EnsemblePosturePredictor

# 전역 예측기 인스턴스
predictor = EnsemblePosturePredictor()