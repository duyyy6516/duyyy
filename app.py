import streamlit as st
import pandas as pd
import numpy as np
import paho.mqtt.client as mqtt
import requests
import json
import time
import random  
from datetime import datetime

# Cấu hình giao diện chuẩn Dashboard cao cấp
st.set_page_config(page_title="Hệ Thống VPD Giám Sát Tối Cao", page_icon="🌿", layout="wide")

st.title("🌿 Hệ Thống Giám Sát VPD Tối Cao & Điều Phối 5 Trạm")
st.markdown("Mô phỏng chu kỳ quét cuốn chiếu: **Mỗi trạm gửi cách nhau 150s, lệch pha nhau đúng 30s**.")

# --- CẤU HÌNH THÔNG TIN KẾT NỐI (BOT CHẠY 1 MÌNH) ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "vuon_thong_minh/duy_tran/sensors"
TELEGRAM_TOKEN = "8924137204:AAGcMCbi6xfxb5LN3KaB1t69YFXc0MjadWk"   
TELEGRAM_CHAT_ID = "7290661009"                                      

# --- KHỞI TẠO STATE ---
if "mqtt_df" not in st.session_state:
    st.session_state.mqtt_df = pd.DataFrame()

if "is_running" not in st.session_state:
    st.session_state.is_running = True

if "current_station_index" not in st.session_state:
    st.session_state.current_station_index = 0

STATIONS_LIST = ["1", "2", "3", "4", "5"]

# =====================================================================
# BANEL ĐIỀU KHIỂN & CẤU HÌNH NGƯỠNG (THIẾT KẾ SIDEBAR GỌN GÀNG)
# =====================================================================
st.sidebar.header("🎮 Trung Tâm Điều Hành")
col_sidebar_start, col_sidebar_stop = st.sidebar.columns(2)
with col_sidebar_start:
    if st.sidebar.button("▶️ BẮT ĐẦU", use_container_width=True, type="primary"):
        st.session_state.is_running = True
        st.rerun()
with col_sidebar_stop:
    if st.sidebar.button("⏸️ DỪNG LẠI", use_container_width=True):
        st.session_state.is_running = False
        st.rerun()

if st.sidebar.button("🗑️ XÓA NHẬT KÝ SẠCH BỘ NHỚ", use_container_width=True):
    st.session_state.mqtt_df = pd.DataFrame()
    st.sidebar.success("Đã xóa sạch bộ nhớ tạm!")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Cấu Hình Ngưỡng VPD")
low_threshold = st.sidebar.slider("Ngưỡng Thấp (Quá ẩm):", min_value=0.1, max_value=1.0, value=0.4, step=0.05, format="%.2f kPa")
high_threshold = st.sidebar.slider("Ngưỡng Cao (Khô nóng):", min_value=1.0, max_value=3.0, value=1.2, step=0.05, format="%.2f kPa")
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
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=2)
    except: pass

def evaluate_status(vpd, temp, humi, station_id, low_t, high_t, mid_t):
    sid = str(station_id)
    if humi == 0:
        return "🔌 MẤT TÍN HIỆU", f"Trạm {sid} báo độ ẩm 0%.", "Kiểm tra lại giắc nối cảm biến.", "danger"
    if vpd > high_t and temp > 40.0 and humi < 40.0:
        return "🔥 KHÔ NÓNG GẮT", f"Trạm {sid} vượt ngưỡng khô gắt ({vpd} kPa).", "KÉO LƯỚI LAN ĐEN, BẬT PHUN SƯƠNG BÙ ẨM KHẨN CẤP!", "danger"
    if humi >= 99.5 or vpd == 0:
        return "⚠️ BÃO HÒA ẨM", f"Trạm {sid} báo độ ẩm chạm trần {humi}%.", "Bật quạt hút đuổi ẩm, NGỪNG tưới nước ngay!", "warning"
    if vpd < low_t:
        return " Nhà kính quá ẩm", f"VPD thấp hơn mốc cài đặt ({vpd} kPa).", "Bật quạt đối lưu, mở cửa hông thoát hơi ẩm.", "warning"
    elif low_t <= vpd < mid_t:
        return " Mát mẻ lý tưởng", f"VPD nằm trong khoảng ẩm dịu ngọt ({vpd} kPa).", "Mọi thứ bình thường. Duy trì.", "success"
    elif mid_t <= vpd <= high_t:
        return " Điểm vàng quang hợp", f"VPD đạt điểm vàng nuôi quả ({vpd} kPa).", "Thời điểm vàng. Giữ nguyên chế độ vườn.", "success"
    
    if humi < 40.0:
        return " Khô hanh nhẹ", f"VPD vượt ngưỡng nhẹ ({vpd} kPa).", "Bật hệ thống phun sương giữa vườn bù độ ẩm.", "warning"
    else:
        return " Nhiệt tăng cao", f"Nhiệt độ nhà màng hầm nóng ({temp}°C).", "Tăng thời gian tưới nhỏ giọt dưới gốc cấp nước cho rễ.", "warning"

def process_incoming_data(df_new):
    if df_new.empty: return
    low_t, high_t, mid_t = st.session_state.low_threshold, st.session_state.high_threshold, st.session_state.mid_threshold
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
            status, reason, action, _ = evaluate_status(vpd_val, t_val, h_val, station_id, low_t, high_t, mid_t)
            
            msg = (
                f"📡 *[HỆ THỐNG CAO CẤP] TRẠM {station_id}/5*\n"
                f"⏱ Cập nhật: `{str(row[time_col])}`\n"
                f"🌡 {t_val}°C | 💧 {h_val}% | 💨 VPD: *{vpd_val} kPa*\n"
                f"📢 Trạng thái: *{status}*\n"
                f"🛠 Hướng xử lý: _{action}_"
            )
            send_telegram_auto(msg)

    if st.session_state.mqtt_df.empty: st.session_state.mqtt_df = df_new
    else: st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, df_new], ignore_index=True).drop_duplicates(subset=[stt_col, time_col]).tail(100)

# --- CƠ CHẾ LẮNG NGHE MQTT ---
def on_message(client, userdata, message):
    try:
        payload_str = message.payload.decode("utf-8")
        df_new = pd.DataFrame(json.loads(payload_str))
        process_incoming_data(df_new)
    except: pass

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
# THUẬT TOÁN GIẢ LẬP ĐIỀU PHỐI XOAY VÒNG 30 GIÂY
# =====================================================================
idx = st.session_state.current_station_index
active_station = STATIONS_LIST[idx]

if st.session_state.is_running:
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scenarios = ["NORMAL", "MAX_HUMIDITY", "EXTREME_HOT", "LOST_SIGNAL"]
    scenario = random.choices(scenarios, weights=[0.85, 0.07, 0.05, 0.03], k=1)[0]
    
    if scenario == "NORMAL":
        temp, humi = round(random.uniform(26.5, 35.5), 1), round(random.uniform(55.0, 82.0), 1)
    elif scenario == "EXTREME_HOT":
        temp, humi = round(random.uniform(40.5, 43.5), 1), round(random.uniform(25.0, 38.0), 1)
    elif scenario == "MAX_HUMIDITY":
        temp, humi = round(random.uniform(19.0, 24.0), 1), round(random.uniform(99.5, 100.0), 1)
    elif scenario == "LOST_SIGNAL":
        temp, humi = round(random.uniform(25.0, 32.0), 1), 0.0

    mock_packet = [{"time": current_time_str, "station": "5", "tempKK": temp, "humiKK": humi}] if active_station == "5" else [{"Thời gian": current_time_str, "STT": active_station, "Nhiệt độ": temp, "Độ ẩm": humi}]
    process_incoming_data(pd.DataFrame(mock_packet))
    st.session_state.current_station_index = (idx + 1) % len(STATIONS_LIST)

# =====================================================================
# BÀN THÔNG TIN TỔNG QUAN ĐỒNG BỘ (DASHBOARD METRICS)
# =====================================================================
df = st.session_state.mqtt_df.copy()

if not df.empty:
    time_col = 'Thời gian' if 'Thời gian' in df.columns else 'time'
    stt_col = 'STT' if 'STT' in df.columns else 'station'
    df[time_col], df[stt_col] = df[time_col].astype(str), df[stt_col].astype(str)
    
    processed_chunks = []
    danger_count = 0
    warning_count = 0
    all_vpds = []

    for station_id in STATIONS_LIST:
        station_df = df[df[stt_col] == station_id]
        if station_df.empty: continue
        row = station_df.tail(1).iloc[0]
        t_col = 'tempKK' if station_id == "5" else ('Nhiệt Độ' if 'Nhiệt Độ' in df.columns else 'Nhiệt độ')
        h_col = 'humiKK' if station_id == "5" else 'Độ ẩm'
        
        if t_col in df.columns and h_col in df.columns:
            t_val, h_val = pd.to_numeric(row[t_col]), pd.to_numeric(row[h_col])
            if station_id != "5" and t_val > 100: t_val /= 10.0
            if station_id != "5" and h_val > 100: h_val /= 10.0
            
            vpd_val = round(calculate_vpd(t_val, h_val), 3)
            all_vpds.append(vpd_val)
            status, reason, action, color_type = evaluate_status(vpd_val, t_val, h_val, station_id, low_threshold, high_threshold, mid_threshold)
            
            if color_type == "danger": danger_count += 1
            elif color_type == "warning": warning_count += 1
            
            processed_chunks.append({
                "Mốc Thời Gian": row[time_col], "Mã Số Trạm": f"Trạm {station_id}",
                "Nhiệt độ (°C)": t_val, "Độ ẩm (%)": h_val, "VPD (kPa)": vpd_val,
                "Trạng Thái": status, "Lý Do Hệ Thống": reason, "Hành Động Sửa Chữa": action, "Màu": color_type
            })

    # Vẽ 3 thẻ KPI hàng đầu cực đẹp
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("🌡️ VPD Toàn Viện (Trung Bình)", f"{round(np.mean(all_vpds), 2) if all_vpds else 0.0} kPa")
    with m2: st.metric("🚨 Số Trạm Báo Động Nguy Hiểm", f"{danger_count} Trạm", delta=f"{danger_count} lỗi khẩn cấp", delta_color="inverse" if danger_count > 0 else "normal")
    with m3: st.metric("⚠️ Số Trạm Cần Lưu Ý Cân Bằng", f"{warning_count} Trạm")

    # --- ĐỒ THỊ REAL-TIME GRAPH ---
    st.subheader("📈 Đồ Thị Biến Thiên Chỉ Số VPD Toàn Vườn")
    if processed_chunks:
        df_chart = pd.DataFrame(processed_chunks)
        df_pivot = df_chart.pivot_table(index="Mốc Thời Gian", columns="Mã Số Trạm", values="VPD (kPa)")
        st.line_chart(df_pivot, height=220)

    # --- BẢNG SỐ LIỆU ĐƯỢC ĐỔ MÀU PHÂN LOẠI ---
    st.subheader("🔔 Bảng Quản Lý Trạng Thái Chi Tiết")
    if processed_chunks:
        df_final = pd.DataFrame(processed_chunks)
        
        # Hàm tô màu dòng thông minh dựa vào loại cảnh báo
        def color_row(row):
            if row['Màu'] == 'danger': return ['background-color: #ffcccc; color: black'] * len(row)
            elif row['Màu'] == 'warning': return ['background-color: #fff2cc; color: black'] * len(row)
            return ['background-color: #e2f0d9; color: black'] * len(row)
            
        df_display = df_final.drop(columns=["Màu"])
        st.dataframe(df_display.style.apply(color_row, axis=1), use_container_width=True)

else:
    st.info("🔌 Đang nạp hệ thống đồ thị và phân phối vòng tròn...")

# =====================================================================
# BỘ ĐẾM NGƯỢC THỜI GIAN NHỊP 30 GIÂY
# =====================================================================
countdown_placeholder = st.empty()
if st.session_state.is_running:
    for seconds_left in range(30, 0, -1):
        countdown_placeholder.markdown(f"⏳ **Xung nhịp quét cuốn chiếu:** Lượt tiếp theo sau `{seconds_left} giây`...")
        time.sleep(1)
    st.rerun()
else:
    countdown_placeholder.markdown("⏸️ **Hệ thống đang tạm dừng.**")
