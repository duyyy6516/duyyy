import streamlit as st
import pandas as pd
import numpy as np
import paho.mqtt.client as mqtt
import requests
import json
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CẤU HÌNH ---
st.set_page_config(page_title="Giám Sát Trạm Đơn", page_icon="🚨", layout="wide")
st.title("🚨 Hệ Thống Giám Sát Real-Time (1 Trạm)")

MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "vuon_thong_minh/duy_tran/sensors"
TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN" 
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

# --- STATE ---
if "mqtt_df" not in st.session_state:
    st.session_state.mqtt_df = pd.DataFrame()

# --- CẤU HÌNH NGƯỠNG ---
PLANT_PRESETS = {
    "Tự tùy chỉnh": None,
    "🥒 Dưa leo": (0.70, 1.30),
    "🍅 Cà chua": (0.60, 1.20),
    "🫑 Ớt chuông": (0.50, 1.00),
    "🌹 Hoa hồng": (0.80, 1.20)
}

with st.sidebar:
    st.subheader("⚙️ Cài Đặt")
    selected_plant = st.selectbox("Chọn cây:", list(PLANT_PRESETS.keys()))
    low_t = st.slider("VPD Thấp:", 0.1, 1.5, 0.45, 0.05)
    high_t = st.slider("VPD Cao:", 1.0, 3.0, 1.70, 0.05)

# --- LOGIC TÍNH TOÁN ---
def calculate_vpd(temp, humi):
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    return round(float(np.clip(vp_sat * (1 - (humi / 100)), 0, None)), 3)

# --- MQTT CALLBACK ---
def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode())
        df_new = pd.DataFrame([data])
        
        # ⚠️ ĐẢM BẢO TÊN CỘT TRÙNG KHỚP VỚI JSON TRẢ VỀ
        # Nếu thiết bị gửi lên key là 'Nhiệt độ' thì phải dùng 'Nhiệt độ'
        t_val = df_new['Nhiệt độ'][0] 
        h_val = df_new['Độ ẩm'][0]
        
        df_new['VPD'] = calculate_vpd(t_val, h_val)
        df_new['Thời gian'] = datetime.now().strftime("%H:%M:%S")
        
        st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, df_new]).tail(50)
        
        # Logic cảnh báo
        if df_new['VPD'][0] > high_t:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": f"⚠️ VPD cao: {df_new['VPD'][0]}"})
    except Exception as e:
        st.error(f"Lỗi xử lý MQTT: {e}")

# Khởi tạo Client MQTT
@st.cache_resource
def start_mqtt():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(MQTT_TOPIC)
    client.on_message = on_message
    client.loop_start()
    return client

start_mqtt()

# --- GIAO DIỆN ---
st_autorefresh(interval=30000, key="refresh")

df = st.session_state.mqtt_df
if not df.empty:
    latest = df.iloc[-1]
    col1, col2, col3 = st.columns(3)
    # ⚠️ Sử dụng đúng key: 'Nhiệt độ' và 'Độ ẩm'
    col1.metric("🌡️ Nhiệt độ", f"{latest['Nhiệt độ']}°C")
    col2.metric("💧 Độ ẩm", f"{latest['Độ ẩm']}%")
    col3.metric("💨 VPD", f"{latest['VPD']} kPa")

    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Tải dữ liệu CSV", csv, "log_tram.csv", "text/csv")

    st.line_chart(df.set_index("Thời gian")[["Nhiệt độ", "VPD"]])
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)
else:
    st.warning("Đang chờ dữ liệu...")
