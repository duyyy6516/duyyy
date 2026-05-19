import streamlit as st
import pandas as pd
import numpy as np
import paho.mqtt.client as mqtt
import requests
import json
import time
import random  
from datetime import datetime

# =====================================================================
# CẤU HÌNH GIAO DIỆN DI ĐỘNG
# =====================================================================
st.set_page_config(page_title="Hệ Thống Quét Điều Khiển", page_icon="🚨", layout="centered")

st.title("🚨 Giám Sát Real-Time Quét Vòng 5 Trạm")
st.markdown("Mô phỏng: **Mỗi trạm gửi cách nhau 150s, các trạm lệch pha nhau đúng 30s**.")

# --- CẤU HÌNH THÔNG TIN KẾT NỐI (BOT CHẠY 1 MÌNH) ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "vuon_thong_minh/duy_tran/sensors"
TELEGRAM_TOKEN = "8924137204:AAGcMCbi6xfxb5LN3KaB1t69YFXc0MjadWk"   
TELEGRAM_CHAT_ID = "7290661009"                                      

# --- KHỞI TẠO STATE ---
if "mqtt_df" not in st.session_state:
    st.session_state.mqtt_df = pd.DataFrame()

# Trạng thái hoạt động của bộ giả lập (Mặc định là chạy tự động)
if "is_running" not in st.session_state:
    st.session_state.is_running = True

# Biến lưu vết trạm nào sẽ gửi ở giây thứ mấy
if "current_station_index" not in st.session_state:
    st.session_state.current_station_index = 0

# Danh sách 5 trạm trong hệ thống vườn
STATIONS_LIST = ["1", "2", "3", "4", "5"]

# =====================================================================
# BỘ ĐIỀU KHIỂN BẮT ĐẦU / DỪNG LẠI (PLAY / PAUSE BUTTONS)
# =====================================================================
st.subheader("🎮 Bộ Điều Khiển Hệ Thống")
col_start, col_stop = st.columns(2)

with col_start:
    if st.button("▶️ BẮT ĐẦU (Chạy tự động)", use_container_width=True, type="primary"):
        st.session_state.is_running = True
        st.rerun()

with col_stop:
    if st.button("⏸️ DỪNG LẠI (Tạm dừng quét)", use_container_width=True):
        st.session_state.is_running = False
        st.rerun()

# Hiển thị thanh thông báo trạng thái hiện tại của máy học ngầm
if st.session_state.is_running:
    st.success("🤖 Hệ thống đang: **CHẠY TỰ ĐỘNG (Xung nhịp 30s)**")
else:
    st.warning("⏸️ Hệ thống đang: **TẠM DỪNG QUÉT** (Đang giữ nguyên thông số hiển thị và CHẶN tin nhắn)")

# =====================================================================
# CẤU HÌNH THANH TRƯỢT NGƯỠNG ĐỘNG
# =====================================================================
st.subheader("⚙️ Cài Đặt Ngưỡng VPD")
low_threshold = st.slider("1. Ngưỡng VPD Thấp (Quá ẩm):", min_value=0.1, max_value=1.0, value=0.4, step=0.05, format="%.2f kPa")
high_threshold = st.slider("2. Ngưỡng VPD Cao (Khô nóng):", min_value=1.0, max_value=3.0, value=1.2, step=0.05, format="%.2f kPa")
mid_threshold = round((low_threshold + high_threshold) / 2, 2)

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
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=2)
    except: 
        pass

def evaluate_status(vpd, temp, humi, station_id, low_t, high_t, mid_t):
    sid = str(station_id)
    
    # 1. Các trạng thái lỗi phần cứng hoặc cực đoan nguy hiểm (Ưu tiên check trước)
    if humi == 0:
        return "🔌 Mất tín hiệu thiết bị", f"Trạm {sid} báo độ ẩm bằng 0%.", "Kiểm tra lại dây nguồn, giắc nối đầu dò."
    
    if vpd > high_t and temp > 40.0 and humi < 40.0:
        return "🔥 BÁO ĐỘNG: KHÔ NÓNG GẮT", f"Trạm {sid} vượt ngưỡng khô gắt cài đặt ({vpd} kPa).", "CHẠY RA KÉO LƯỚI LAN ĐEN CẤT NẮNG, BẬT PHUN SƯƠNG BÙ ẨM KHẨN CẤP!"
        
    if humi >= 99.5 or vpd == 0:
        return "⚠️ THÔNG BÁO: BÃO HÒA ẨM", f"Trạm {sid} báo độ ẩm chạm trần {humi}%.", "Bật ngay quạt hút đuổi ẩm và ngừng tưới nước ngay!"

    # 2. Các khoảng môi trường ĐÚNG / LÝ TƯỞNG dựa trên thanh trượt cài đặt
    if vpd < low_t:
        return "Nhà kính quá ẩm", f"VPD thấp hơn mốc cài đặt ({vpd} < {low_t} kPa).", "Bật quạt đối lưu, mở cửa hông để thoát bớt hơi ẩm."
        
    elif low_t <= vpd < mid_t:
        return "Môi trường mát mẻ lý tưởng", f"VPD nằm trong khoảng ẩm dịu ngọt ({vpd} kPa).", "Mọi thứ bình thường. Tiếp tục duy trì."
        
    elif mid_t <= vpd <= high_t:
        return "Thời tiết hoàn hảo", f"VPD đạt điểm vàng quang hợp ({vpd} kPa).", "Thời điểm vàng nuôi quả lớn. Giữ nguyên chế độ vườn."
        
    # 3. Khi vượt qua tất cả các khoảng lý tưởng ở trên (Nghĩa là chắc chắn VPD > high_t)
    else:
        if humi < 40.0:
            return "Môi trường khô hanh", f"VPD vượt ngưỡng cao ({vpd} kPa) do thiếu ẩm.", "Bật hệ thống phun sương giữa vườn để bù lại độ ẩm."
        else:
            return "Nhiệt độ tăng cao", f"Nhiệt độ nhà màng hầm nóng ({temp}°C) làm đẩy VPD lên {vpd} kPa.", "Tăng thời gian tưới nhỏ giọt dưới gốc cấp nước cho rễ."

def process_incoming_data(df_new):
    if df_new.empty:
        return

    # CHẶN TUYỆT ĐỐI: Nếu hệ thống đang bấm DỪNG LẠI thì thoát ngay, không lưu, không gửi Telegram
    if "is_running" in st.session_state and not st.session_state.is_running:
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
            
            status, reason, action = evaluate_status(vpd_val, t_val, h_val, station_id, low_t, high_t, mid_t)
            
            msg = (
                f"📡 *[MÔ PHỎNG REALTIME] TRẠM {station_id}/5*\n"
                f"⏱ Cập nhật: `{time_log}`\n"
                f"🌡 Nhiệt độ: {t_val}°C | 💧 Độ ẩm: {h_val}%\n"
                f"💨 Chỉ số VPD: *{vpd_val} kPa*\n"
                f"📢 Trạng thái: *{status}*\n"
                f"🛠 Hướng xử lý: _{action}_"
            )
            send_telegram_auto(msg)

    # Đảm bảo đồng bộ tên cột thống nhất trước khi concat vào Database lưu trữ tạm thời của Session
    df_normalized = df_new.copy()
    if 'time' in df_normalized.columns: df_normalized.rename(columns={'time': 'Thời gian'}, inplace=True)
    if 'station' in df_normalized.columns: df_normalized.rename(columns={'station': 'STT'}, inplace=True)
    if 'tempKK' in df_normalized.columns: df_normalized.rename(columns={'tempKK': 'Nhiệt độ'}, inplace=True)
    if 'humiKK' in df_normalized.columns: df_normalized.rename(columns={'humiKK': 'Độ ẩm'}, inplace=True)
    if 'Nhiệt Độ' in df_normalized.columns: df_normalized.rename(columns={'Nhiệt Độ': 'Nhiệt độ'}, inplace=True)

    if st.session_state.mqtt_df.empty:
        st.session_state.mqtt_df = df_normalized
    else:
        st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, df_normalized], ignore_index=True).drop_duplicates(subset=['STT', 'Thời gian']).tail(200)

# --- CƠ CHẾ LẮNG NGHE MQTT ---
def on_message(client, userdata, message):
    try:
        payload_str = message.payload.decode("utf-8")
        new_data = json.loads(payload_str)
        df_new = pd.DataFrame(new_data)
        process_incoming_data(df_new)
    except:
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
# THUẬT TOÁN GIẢ LẬP LỆCH PHA 30 GIÂY (CHỈ CHẠY KHI IS_RUNNING = TRUE)
# =====================================================================
st.subheader("⏱️ Tiến Độ Điều Phối Xung Nhịp")

idx = st.session_state.current_station_index
active_station = STATIONS_LIST[idx]
next_station = STATIONS_LIST[(idx + 1) % len(STATIONS_LIST)]

# Hiển thị thông số trạm đang chờ điều phối lên màn hình
col1, col2 = st.columns(2)
with col1:
    st.metric(label="🟢 Trạm vừa xử lý dữ liệu", value=f"Trạm {active_station}")
with col2:
    st.metric(label="⏳ Trạm xếp hàng kế tiếp", value=f"Trạm {next_station}")

# CHỈ SINH DỮ LIỆU KHI TRẠNG THÁI ĐANG BẬT CHẠY
if st.session_state.is_running:
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # -----------------------------------------------------------------
    # NÚT CHỐT RESET: Nếu bắt đầu quay về Trạm 1 -> Xóa sạch dữ liệu cũ
    # -----------------------------------------------------------------
    if active_station == "1":
        st.session_state.mqtt_df = pd.DataFrame()
    # -----------------------------------------------------------------

    scenarios = ["NORMAL", "MAX_HUMIDITY", "EXTREME_HOT", "LOST_SIGNAL"]
    weights = [0.85, 0.07, 0.05, 0.03]
    scenario = random.choices(scenarios, weights=weights, k=1)[0]
    
    if scenario == "NORMAL":
        temp = round(random.uniform(26.5, 35.5), 1)
        humi = round(random.uniform(55.0, 82.0), 1)
    elif scenario == "EXTREME_HOT":
        temp = round(random.uniform(40.5, 43.5), 1)
        humi = round(random.uniform(25.0, 38.0), 1)
    elif scenario == "MAX_HUMIDITY":
        temp = round(random.uniform(19.0, 24.0), 1)
        humi = round(random.uniform(99.5, 100.0), 1)
    elif scenario == "LOST_SIGNAL":
        temp = round(random.uniform(25.0, 32.0), 1)
        humi = 0.0

    if active_station == "5":
        mock_packet = [{"time": current_time_str, "station": "5", "tempKK": temp, "humiKK": humi}]
    else:
        mock_packet = [{"Thời gian": current_time_str, "STT": active_station, "Nhiệt độ": temp, "Độ ẩm": humi}]
        
    df_single_step = pd.DataFrame(mock_packet)
    process_incoming_data(df_single_step)
    
    # Chuẩn bị tăng vị trí lên trạm kế tiếp cho lượt sau
    st.session_state.current_station_index = (idx + 1) % len(STATIONS_LIST)


# Vùng hiển thị đồng hồ đếm ngược trực quan trên Web
countdown_placeholder = st.empty()

# =====================================================================
# BIỂU DIỄN BẢNG DỮ LIỆU LÊN APP SCREEN (TỰ ĐỘNG RESET THEO VÒNG)
# =====================================================================
df = st.session_state.mqtt_df.copy()

st.subheader("🔔 Bảng Trạng Thái 5 Trạm Chu Kỳ Hiện Tại")
processed_chunks = []

# Luôn luôn quét hiển thị cố định từ Trạm 1 đến Trạm 5
for station_id in STATIONS_LIST:
    station_df = pd.DataFrame()
    if not df.empty:
        station_df = df[df['STT'].astype(str) == str(station_id)]
    
    # Nếu trạm này chưa được quét trúng ở vòng hiện tại (Do vừa bị Reset hoặc mới bật app)
    if station_df.empty:
        processed_chunks.append(pd.DataFrame([{
            "Thời gian": "Đang chờ lượt...",
            "Số Trạm": f"Trạm {station_id}",
            "Nhiệt độ (°C)": None,
            "Độ ẩm (%)": None,
            "VPD (kPa)": None,
            "Trạng Thái Vườn": "💤 Đang chờ quét vòng",
            "Lý Do Từ Cảm Biến": "-",
            "Hành Động Khắc Phục": "-"
        }]))
        continue
        
    # Nếu có dữ liệu trong chu kỳ hiện tại, lấy dòng mới nhất
    row = station_df.sort_values(by='Thời gian', ascending=True).tail(1).iloc[0]
    
    t_val = pd.to_numeric(row['Nhiệt độ'])
    h_val = pd.to_numeric(row['Độ ẩm'])
    
    if str(station_id) != "5" and t_val > 100: t_val /= 10.0
    if str(station_id) != "5" and h_val > 100: h_val /= 10.0
    
    vpd_val = round(calculate_vpd(t_val, h_val), 3)
    status, reason, action = evaluate_status(vpd_val, t_val, h_val, station_id, low_threshold, high_threshold, mid_threshold)
    
    processed_chunks.append(pd.DataFrame([{
        "Thời gian": row['Thời gian'],
        "Số Trạm": f"Trạm {station_id}",
        "Nhiệt độ (°C)": t_val,
        "Độ ẩm (%)": h_val,
        "VPD (kPa)": vpd_val,
        "Trạng Thái Vườn": status,
        "Lý Do Từ Cảm Biến": reason,
        "Hành Động Khắc Phục": action
    }]))
        
if processed_chunks:
    final_table = pd.concat(processed_chunks, ignore_index=True)
    st.dataframe(final_table, use_container_width=True)


# =====================================================================
# QUẢN LÝ VÒNG LẶP THỜI GIAN THEO TRẠNG THÁI NÚT BẤM
# =====================================================================
if st.session_state.is_running:
    # Nếu hệ thống đang bật -> Tiến hành chạy vòng lặp đếm ngược 30 giây
    for seconds_left in range(30, 0, -1):
        countdown_placeholder.markdown(f"⏳ **Đang đếm ngược chu kỳ lệch pha:** `{seconds_left} giây nữa` sẽ chuyển sang trạm kế tiếp...")
        time.sleep(1)
    st.rerun()
else:
    # Nếu hệ thống đã bị Dừng lại (Pause) -> Treo tĩnh màn hình tại đây, không đếm ngược nữa
    countdown_placeholder.markdown("⏸️ **Bộ đếm thời gian tự động đang dừng.** Nhấn nút Bắt đầu phía trên để kích hoạt lại chu kỳ.")
