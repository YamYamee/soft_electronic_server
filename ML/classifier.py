import serial
import time
import joblib
import numpy as np
import sys
from sklearn.preprocessing import StandardScaler

# ★★★ 환경 설정 ★★★
SERIAL_PORT = 'COM5'
BAUD_RATE = 9600
MODEL_FILENAME = 'models/model_lr.joblib'
SCALER_FILENAME = 'models/scaler.joblib'
# CALIBRATION_DATA_COUNT = 30 # 보정 데이터 개수 설정 (10개)

def setup_serial_connection(port, baudrate):
    """시리얼 포트를 열고 아두이노와의 연결을 설정합니다."""
    print("아두이노와 시리얼 연결 시도...")
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  # 아두이노 리셋 대기
        print(f"✅ 연결 성공: {port} @ {baudrate} bps")
        return ser
    except serial.SerialException as e:
        print(f"❌ 오류: 시리얼 포트를 열 수 없습니다. '{port}'. {e}")
        print("1) 장치 연결 확인 2) 포트 이름 확인 3) 다른 프로그램이 포트 사용 중인지 확인")
        return None

def main():
    print("start")
    ser = setup_serial_connection(SERIAL_PORT, BAUD_RATE)
    if ser is None:
        return
    
    model = joblib.load(MODEL_FILENAME)
  

    # ★★★ 표준화를 위한 변수 및 단계 초기화
    # is_calibrating = True
    # calibration_data = []
    # calibration_mean = None
    # calibration_std = None
    ss=joblib.load(SCALER_FILENAME)
    scaler_mean=ss.mean_
    scaler_std=ss.scale_
    data_counter = 0 # 5번째 데이터마다 처리하기 위한 카운터

    print("\n데이터 수신을 시작합니다. 중지하려면 'Ctrl+C'를 누르세요.")
    print(f"scaler 평균: {scaler_mean}")
    print(f"scaler 표준편차: {scaler_std}")
    # print(f"⚠️ 처음 {CALIBRATION_DATA_COUNT}개의 데이터로 표준화 기준을 설정합니다.")
    
    try:
        while True:
            if ser.in_waiting > 0:
                try:
                    raw = ser.readline()
                    if not raw:
                        continue
                    line = raw.decode('utf-8', errors='replace').strip()
                except Exception as e:
                    print(f"경고: 시리얼 디코딩 오류 - {e}")
                    continue

                if line:
                    try:
                        # 쉼표로 분리하여 숫자형 리스트로 변환
                        parts = [float(p) for p in line.split(',') if p.strip()]
                        
                        # # ★★★ 보정(Calibration) 단계 실행
                        # if is_calibrating:
                        #     calibration_data.append(parts)
                        #     print(f"보정 데이터 수집 중... ({len(calibration_data)}/{CALIBRATION_DATA_COUNT})")
                            
                        #     # 보정 데이터 개수가 10개에 도달했는지 확인
                        #     if len(calibration_data) >= CALIBRATION_DATA_COUNT:
                        #         calibration_data_np = np.array(calibration_data)
                        #         calibration_mean = np.mean(calibration_data_np, axis=0)
                        #         calibration_std = np.std(calibration_data_np, axis=0)
                        #         # 표준편차가 0인 경우를 방지 (0으로 나누기 오류)
                        #         calibration_std[calibration_std == 0] = 1e-9
                                
                        #         is_calibrating = False
                        #         print("\n✅ 보정 완료! 이후 모든 데이터는 표준화되어 예측에 사용됩니다.")
                        #         print(f"**보정 기준 (평균/표준편차):**")
                        #         print(f"평균: {calibration_mean}")
                        #         print(f"표준편차: {calibration_std}")

                        # ★★★ 실시간 예측 단계
                        # else:
                        data_counter += 1
                        
                        # 5번째 데이터마다 예측을 수행
                        if data_counter % 5 == 0:
                            # 1. 수신 데이터를 NumPy 배열로 변환
                            data_to_predict = np.array(parts).reshape(1, -1)
                            
                            # 2. 데이터를 보정 기준(평균, 표준편차)으로 표준화
                            standardized_data = (data_to_predict - scaler_mean) / scaler_std
                            
                            # 3. 모델 예측 수행
                            prediction = model.predict(standardized_data)
                            # prediction = model.predict(data_to_predict)
                            
                            # 4. 예측 결과와 함께 데이터 출력
                            print(f"({data_counter}번째 데이터) 수신 데이터: {line}| 예측 결과: {prediction}")
                            print(f"({data_counter}번째 데이터) 수신 데이터: {standardized_data} | 예측 결과: {prediction}")
                            print("\n")
                            # formatted_data = [f"{x:.4f}" for x in standardized_data[0]] # standardized_data는 2차원 배열이므로 [0]으로 접근
                            # # formatted_data_str = ", ".join(formatted_data)
                            # print(f"({data_counter}번째 데이터) 수신 데이터: {formatted_data} | 예측 결과: {prediction}")
                            
                    except ValueError:
                        print(f"경고: 올바른 형식의 데이터가 아닙니다 - {line}")
                    except Exception as e:
                        print(f"경고: 처리 중 오류 발생 - {e}")
            
            # CPU 사용량 최소화를 위해 잠시 대기
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("시리얼 포트가 닫혔습니다.")

if __name__ == "__main__":
    main()