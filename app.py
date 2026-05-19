import streamlit as st
import pandas as pd
import numpy as np
import paho.mqtt.client as mqtt
import requests
import json
import time
import random  # Thêm thư viện để tạo dữ liệu ngẫu nhiên
from datetime import datetime

# Cấu hình giao diện di động
st.set_page_config(page_title="Hệ Thống MQTT Real-Time", page_icon="🚨", layout="centered")

st.title("🚨 Hệ Thống VPD Real-Time Qua MQTT")
st.markdown("Ứng dụng đang nghe tín hiệu trực tiếp từ cảm biến qua giao thức **MQTT 30 giây/lần**.")

# --- CẤU HÌNH THÔNG TIN KẾT NỐI MỚI (BOT CHẠY 1 MÌNH) ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "vuon_thong_minh/duy_tran/sensors"
TELEGRAM_TOKEN = "8924137204:AAGcMCbi6xfxb5LN3KaB1t69YFXc0MjadWk"   
TELEGRAM_CHAT_ID = "7290661009"                                      

# --- KHỞI TẠO STATE ---
if "mqtt_df" not in st.session_state:
    st.session_state.mqtt_df = pd.DataFrame()

# Lưu vết cảnh báo gần nhất của từng trạm để tránh spam Telegram
if "last_alerts" not in st.session_state:
    st.session_state.last_alerts = {} 

# =====================================================================
# CẤU HÌNH THANH TRƯỢT NGƯỠNG ĐỘNG
# =====================================================================
st.subheader("⚙️ Cài Đặt Ngưỡng VPD")
low_threshold = st.slider("1. Ngưỡng VPD Thấp (Quá ẩm):", min_value=0.1, max_value=1.0, value=0.4, step=0.05, format="%.2f kPa")
high_threshold = st.slider("2. Ngưỡng VPD Cao (Khô nóng):", min_value=1.0, max_value=3.0, value=1.2, step=0.05, format="%.2f kPa")
mid_threshold = round((low_threshold + high_threshold) / 2, 2)

# Cập nhật ngưỡng vào session_state để hàm MQTT chạy ngầm hoặc nút bấm đọc được
st.session_state.low_threshold = low_threshold
st.session_state.high_threshold = high_threshold
st.session_state.mid_threshold = mid_threshold

# =====================================================================
# LOGIC TOÁN HỌC VÀ ĐÁNH GIÁ TRẠNG THÁI
# =====================================================================

def calculate_vpd(temp, humi):
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    return float(np.clip(vp_sat * (1 - (humi / 100)), 0, None))

def send_telegram_auto(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: 
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=3)
    except: 
        pass

def evaluate_status(vpd, temp, humi, station_id, low_t, high_t, mid_t):
    sid = str(station_id)
    if humi == 0:
        return "Mất tín hiệu thiết bị", f"Trạm {sid} báo độ ẩm bằng 0%.", "Kiểm tra lại dây nguồn, giắc nối đầu dò.", "LOST_SIGNAL"
    
    if vpd > high_t and temp > 40.0 and humi < 40.0:
        return "⚠️ CẢNH BÁO: KHÔ NÓNG GẮT", f"Trạm {sid} vượt ngưỡng khô gắt cài đặt ({vpd} kPa).", "CHẠY RA KÉO LƯỚI LAN ĐEN CẤT NẮNG, BẬT PHUN SƯƠNG BÙ ẨM KHẨN CẤP!", "EXTREME_HOT"
        
    if humi >= 99.5 or vpd == 0:
        return "Không khí ẩm ướt bão hòa", f"Trạm {sid} báo độ ẩm chạm trần {humi}%.", "Bật ngay quạt hút đuổi ẩm và ngừng tưới nước!", "MAX_HUMIDITY"

    if vpd < low_t:
        return "Nhà kính quá ẩm", f"VPD thấp hơn mốc cài đặt ({vpd} < {low_t} kPa).", "Bật quạt đối lưu, mở cửa hông để thoát bớt hơi ẩm.", "LOW_VPD"
    elif low_t <= vpd < mid_t:
        return "Môi trường mát mẻ lý tưởng", f"VPD nằm trong khoảng ẩm dịu ngọt ({vpd} kPa).", "Mọi thứ bình thường. Tiếp tục duy trì.", "IDEAL_VPD"
    elif mid_t <= vpd <= high_t:
        return "Thời tiết hoàn hảo", f"VPD đạt điểm vàng quang hợp ({vpd} kPa).", "Thời điểm vàng nuôi quả lớn. Giữ nguyên chế độ vườn.", "PERFECT_VPD"
    
    if humi < 40.0:
        return "Môi trường khô hanh", f"VPD vượt ngưỡng nhẹ ({vpd} kPa).", "Bật hệ thống phun sương giữa vườn để bù lại độ ẩm.", "DRY_AIR"
    else:
        return "Nhiệt độ tăng cao", f"Nhiệt độ nhà màng hầm nóng ({temp}°C).", "Tăng thời gian tưới nhỏ giọt dưới gốc cấp nước cho rễ.", "HIGH_TEMP"

# --- HÀM XỬ LÝ CHUNG KHI CÓ DỮ LIỆU ĐỔ VỀ (TỪ MQTT HOẶC TỪ RANDOM TEST) ---
def process_incoming_data(df_new):
    if df_new.empty:
        return

    low_t = st.session_state.get("low_threshold", 0.4)
    high_t = st.session_state.get("high_threshold", 1.2)
    mid_t = st.session_state.get("mid_threshold", 0.8)

    time_col = 'Thời gian' if 'Thời gian' in df_new.columns else 'time'
    stt_col = 'STT' if 'STT' in df_new.columns else 'station'

    for _, row in df_new.iterrows():
        station_id = str(row[stt_col])
        t_col = 'tempKK' if station_id == "5" else ('Nhiệt Độ' if 'Nhiệt Độ' in df_new.columns else 'Nhiệt độ')
        h_col = 'humiKK' if station_id == "5" else 'Độ ẩm'
        
        if t_col in row and h_col in row:
            t_val = pd.to_numeric(row[t_col])
            h_val = pd.to_numeric(row[h_col])
            if station_id != "5" and t_val > 100: t_val /= 10.0
            if station_id != "5" and h_val > 100: h_val /= 10.0
            
            vpd_val = round(calculate_vpd(t_val, h_val), 3)
            time_log = str(row[time_col])
            
            _, _, _, alert_code = evaluate_status(vpd_val, t_val, h_val, station_id, low_t, high_t, mid_t)
            
            last_code = st.session_state.last_alerts.get(station_id)
            if alert_code in ["LOST_SIGNAL", "EXTREME_HOT", "MAX_HUMIDITY"]:
                if last_code != alert_code: 
                    if alert_code == "LOST_SIGNAL":
                        msg = f"🔌 *[TEST] MẤT TÍN HIỆU THIẾT BỊ*\n⏱ Cập nhật: {time_log}\n📍 Vị trí: Trạm {station_id}\n📝 *Lý do:* Độ ẩm đột ngột tụt về 0%.\n🛠 *Hành động:* Ra vườn kiểm tra lại cục cảm biến ngay!"
                    elif alert_code == "EXTREME_HOT":
                        msg = f"🔥 *[TEST] BÁO ĐỘNG: KHÔ NÓNG GẮT*\n⏱ Cập nhật: {time_log}\n📍 Vị trí: Trạm {station_id}\n🌡 {t_val}°C | 💧 {h_val}%\n💨 *VPD thực tế:* {vpd_val} kPa\n🛠 *Hành động:* KÉO LƯỚI LAN ĐEN CẤT NẮNG, BẬT PHUN SƯƠNG GẤP!"
                    elif alert_code == "MAX_HUMIDITY":
                        msg = f"⚠️ *[TEST] THÔNG BÁO: BÃO HÒA ẨM*\n⏱ Cập nhật: {time_log}\n📍 Vị trí: Trạm {station_id}\n💧 Độ ẩm chạm trần: {h_val}%\n🛠 *Hành động:* Bật ngay quạt hút đuổi ẩm và ngừng tưới nước ngay!"
                    
                    send_telegram_auto(msg)
                    st.session_state.last_alerts[station_id] = alert_code
            else:
                st.session_state.last_alerts[station_id] = alert_code

    if st.session_state.mqtt_df.empty:
        st.session_state.mqtt_df = df_new
    else:
        st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, df_new], ignore_index=True).drop_duplicates(subset=[stt_col, time_col]).tail(100)

# --- CƠ CHẾ LẮNG NGHE MQTT ---
def on_message(client, userdata, message):
    try:
        payload_str = message.payload.decode("utf-8")
        new_data = json.loads(payload_str)
        df_new = pd.DataFrame(new_data)
        process_incoming_data(df_new)
    except Exception as e:
        pass

@st.cache_resource
def start_mqtt_client():
    mqtt_client = mqtt.Client()
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.subscribe(MQTT_TOPIC)
    mqtt_client.loop_start()
    return mqtt_client

_ = start_mqtt_client()


# =====================================================================
# CHỨC NĂNG RANDOM GIẢ LẬP DỮ LIỆU ĐỂ TEST TELEGRAM
# =====================================================================
st.subheader("🧪 Bộ Công Cụ Giả Lập Dữ Liệu")

if st.button("🎲 Bấm để sinh dữ liệu RANDOM ngẫu nhiên (Gửi test Tele)", use_container_width=True):
    # Các kịch bản test (Ngẫu nhiên chọn 1 trong các kịch bản để dễ kích hoạt cảnh báo)
    scenario = random.choice(["NORMAL", "EXTREME_HOT", "MAX_HUMIDITY", "LOST_SIGNAL"])
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    test_station = random.choice(["1", "2", "5"]) # Giả lập trạm 1, 2 hoặc 5
    
    if scenario == "EXTREME_HOT":
        # Tạo dữ liệu cực đoan gây lỗi khô nóng
        temp = round(random.uniform(41.0, 45.0), 1)
        humi = round(random.uniform(15.0, 35.0), 1)
    elif scenario == "MAX_HUMIDITY":
        # Tạo dữ liệu gây lỗi bão hòa ẩm
        temp = round(random.uniform(22.0, 26.0), 1)
        humi = 100.0
    elif scenario == "LOST_SIGNAL":
        # Tạo lỗi mất tín hiệu
        temp = round(random.uniform(25.0, 30.0), 1)
        humi = 0.0
    else:
        # Dữ liệu vườn bình thường mát mẻ lý tưởng
        temp = round(random.uniform(27.0, 34.0), 1)
        humi = round(random.uniform(55.0, 75.0), 1)

    # Đóng gói dữ liệu test tương thích cấu trúc MQTT cũ
    if test_station == "5":
        mock_data = [{"time": current_time, "station": "5", "tempKK": temp, "humiKK": humi}]
    else:
        mock_data = [{"Thời gian": current_time, "STT": test_station, "Nhiệt độ": temp, "Độ ẩm": humi}]
        
    df_mock = pd.DataFrame(mock_data)
    
    # Đẩy thẳng dữ liệu mock vào bộ xử lý tính toán & bắn cảnh báo về Tele
    process_incoming_data(df_mock)
    st.success(f"Đã giả lập thành công kịch bản **{scenario}** tại Trạm {test_station} ({temp}°C, {humi}%)!")


# --- BIỂU DIỄN DỮ LIỆU LÊN APP SCREEN ---
df = st.session_state.mqtt_df.copy()

if not df.empty:
    time_col = 'Thời gian' if 'Thời gian' in df.columns else 'time'
    stt_col = 'STT' if 'STT' in df.columns else 'station'
    
    df[time_col] = df[time_col].astype(str)
    df[stt_col] = df[stt_col].astype(str)
    df = df.sort_values(by=time_col, ascending=True)
    
    latest_time_log = df[time_col].iloc[-1]
    st.markdown(f"⏱️ **Mốc dữ liệu mới nhất:** `{latest_time_log}`")
    st.subheader("🔔 Nhật Ký Theo Dõi Cảm Biến Real-Time")
    
    processed_chunks = []
    
    for station_id in df[stt_col].unique():
        row = df[df[stt_col] == station_id].tail(1).iloc[0]
        t_col = 'tempKK' if station_id == "5" else ('Nhiệt Độ' if 'Nhiệt Độ' in df.columns else 'Nhiệt độ')
        h_col = 'humiKK' if station_id == "5" else 'Độ ẩm'
        
        if t_col in df.columns and h_col in df.columns and not pd.isna(row[t_col]) and not pd.isna(row[h_col]):
            t_val = pd.to_numeric(row[t_col])
            h_val = pd.to_numeric(row[h_col])
            if station_id != "5" and t_val > 100: t_val /= 10.0
            if station_id != "5" and h_val > 100: h_val /= 10.0
            
            vpd_val = round(calculate_vpd(t_val, h_val), 3)
            status, reason, action, _ = evaluate_status(vpd_val, t_val, h_val, station_id, low_threshold, high_threshold, mid_threshold)
            
            processed_chunks.append(pd.DataFrame([{
                "Thời gian": row[time_col],
                "Số Trạm": station_id,
                "Nhiệt độ (°C)": t_val,
                "Độ ẩm (%)": h_val,
                "VPD (kPa)": vpd_val,
                "Trạng Thái Vườn": status,
                "Lý Do Từ Cảm Biến": reason,
                "Hành Động Khắc Phục": action
            }]))
            
    if processed_chunks:
        st.dataframe(pd.concat(processed_chunks, ignore_index=True), use_container_width=True)

else:
    st.info("🔌 Hệ thống đang mở cổng sóng, chờ thiết bị bắn dữ liệu MQTT qua mạng hoặc nhấn nút Random Test phía trên...")

# Vòng lặp tự động reload giao diện
time.sleep(30)
st.rerun()
