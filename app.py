import streamlit as st
import pandas as pd
import numpy as np
import paho.mqtt.client as mqtt
import requests
import json
import random
import queue
import streamlit.components.v1 as components
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
 
# =====================================================================
# CẤU HÌNH GIAO DIỆN DI ĐỘNG & BẢO MẬT
# =====================================================================
st.set_page_config(page_title="Hệ Thống Quét Điều Khiển", page_icon="🌿", layout="centered")
 
st.title("🌿 Giám Sát Real-Time: Trạm 01")
st.markdown("Mô phỏng: **Dữ liệu được cập nhật tự động mỗi 30s**.")
 
# --- CẤU HÌNH THÔNG TIN KẾT NỐI ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "vuon_thong_minh/duy_tran/sensors"
 
TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN"    
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"                         
 
# --- KHỞI TẠO STATE ---
if "mqtt_df" not in st.session_state:
    st.session_state.mqtt_df = pd.DataFrame()
if "is_running" not in st.session_state:
    st.session_state.is_running = True
 
# =====================================================================
# BỘ TỰ ĐỘNG LÀM MỚI (XUNG NHỊP CHUẨN 30 GIÂY)
# =====================================================================
if st.session_state.is_running:
    st_autorefresh(interval=30000, key="iot_refresh")
 
# =====================================================================
# BỘ ĐIỀU KHIỂN BẮT ĐẦU / DỪNG LẠI
# =====================================================================
st.subheader("⚙️ Bộ Điều Khiển Hệ Thống")
col_start, col_stop = st.columns(2)
 
with col_start:
    if st.button("▶️ BẮT ĐẦU (Chạy tự động)", use_container_width=True, type="primary"):
        st.session_state.is_running = True
        st.rerun()
 
with col_stop:
    if st.button("⏸️ DỪNG LẠI (Tạm dừng quét)", use_container_width=True):
        st.session_state.is_running = False
        st.rerun()
 
# =====================================================================
# CẤU HÌNH THANH TRƯỢT NGƯỠNG VPD
# =====================================================================
PLANT_PRESETS = {
    "Tự tùy chỉnh (Kéo tay)": None,
    "🥒 Dưa leo (Nhà kính)": (0.70, 1.30),
    "🍅 Cà chua (Beef, Cherry)": (0.60, 1.20),
    "🫑 Ớt chuông": (0.50, 1.00),
    "🌹 Hoa hồng cắt cành": (0.80, 1.20)
}
 
if "slider_low" not in st.session_state: st.session_state.slider_low = 0.45
if "slider_high" not in st.session_state: st.session_state.slider_high = 1.70
 
def on_plant_change():
    selected_plant = st.session_state.plant_selector
    if selected_plant != "Tự tùy chỉnh (Kéo tay)":
        st.session_state.slider_low = PLANT_PRESETS[selected_plant][0]
        st.session_state.slider_high = PLANT_PRESETS[selected_plant][1]
 
st.selectbox("🌿 Cấu hình nhanh theo loại cây trồng:", options=list(PLANT_PRESETS.keys()), key="plant_selector", on_change=on_plant_change)
low_threshold = st.slider("1. Ngưỡng VPD Thấp (Quá ẩm):", 0.1, 1.5, key="slider_low")
high_threshold = st.slider("2. Ngưỡng VPD Cao (Khô nóng):", 1.0, 3.0, key="slider_high")
 
# =====================================================================
# LOGIC TOÁN HỌC VÀ ĐÁNH GIÁ
# =====================================================================
def calculate_vpd(temp, humi):
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    return float(np.clip(vp_sat * (1 - (humi / 100)), 0, None))
 
def send_telegram_auto(message):
    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_TOKEN": return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=2)
    except: pass
 
def evaluate_status(vpd, temp, humi, low_t, high_t):
    if humi == 0: return "⚠️ Mất tín hiệu", "Độ ẩm 0%", "Kiểm tra cảm biến"
    if vpd < low_t: return "❌ Quá ẩm", f"VPD {vpd:.2f} < {low_t}", "Bật quạt đối lưu"
    if vpd > high_t: return "❌ Khô hanh", f"VPD {vpd:.2f} > {high_t}", "Bật phun sương"
    return "Môi trường lý tưởng", f"VPD {vpd:.2f} ổn định", "Giữ nguyên"
 
# --- XỬ LÝ DỮ LIỆU ĐẾN (MQTT HOẶC RANDOM) ---
def process_data(t, h, time_log):
    vpd = round(calculate_vpd(t, h), 3)
    status, reason, action = evaluate_status(vpd, t, h, low_threshold, high_threshold)
    
    new_row = pd.DataFrame([{"Thời gian": time_log, "STT": "01", "Nhiệt độ": t, "Độ ẩm": h, "VPD": vpd, "Trạng thái": status}])
    st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, new_row]).tail(100)
    
    if st.session_state.is_running:
        send_telegram_auto(f"Trạm 01: {status}\nVPD: {vpd} kPa\n{reason}")

# --- MQTT LẮNG NGHE ---
def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode())
        process_data(data['Nhiệt độ'], data['Độ ẩm'], datetime.now().strftime("%H:%M:%S"))
    except: pass

@st.cache_resource
def start_mqtt():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    return client

# --- LOGIC RANDOM (MÔ PHỎNG NẾU KHÔNG CÓ MQTT) ---
if st.session_state.is_running:
    # Logic random scenario
    temp = round(random.uniform(25.0, 35.0), 1)
    humi = round(random.uniform(50.0, 85.0), 1)
    process_data(temp, humi, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# =====================================================================
# BẢNG DỮ LIỆU & BIỂU ĐỒ
# =====================================================================
if not st.session_state.mqtt_df.empty:
    st.download_button("📥 Tải CSV", st.session_state.mqtt_df.to_csv(index=False), "data_01.csv")
    st.dataframe(st.session_state.mqtt_df.sort_index(ascending=False), use_container_width=True)
    
    fig = px.line(st.session_state.mqtt_df, x="Thời gian", y="VPD", title="Chỉ số VPD Trạm 01")
    fig.add_hline(y=low_threshold, line_dash="dash", line_color="blue")
    fig.add_hline(y=high_threshold, line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)
