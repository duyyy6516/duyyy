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

# --- LOGIC ---
def calculate_vpd(temp, humi):
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    return round(float(np.clip(vp_sat * (1 - (humi / 100)), 0, None)), 3)

def send_telegram(msg):
    if TELEGRAM_TOKEN != "YOUR_TELEGRAM_TOKEN":
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

# --- MQTT CALLBACK ---
def on_message(client, userdata, message):
    data = json.loads(message.payload.decode())
    df_new = pd.DataFrame([data])
    df_new['VPD'] = calculate_vpd(df_new['temp'][0], df_new['humi'][0])
    df_new['Thời gian'] = datetime.now().strftime("%H:%M:%S")
    
    st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, df_new]).tail(50)
    
    # Logic cảnh báo
    if df_new['VPD'][0] > high_t:
        send_telegram(f"⚠️ Cảnh báo: VPD quá cao ({df_new['VPD'][0]})")

# --- GIAO DIỆN CHÍNH ---
st_autorefresh(interval=30000, key="refresh")

df = st.session_state.mqtt_df
if not df.empty:
    latest = df.iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("🌡️ Nhiệt độ", f"{latest['temp']}°C")
    col2.metric("💧 Độ ẩm", f"{latest['humi']}%")
    col3.metric("💨 VPD", f"{latest['VPD']} kPa")

    # Nút CSV chuẩn Excel
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Tải dữ liệu CSV", csv, "log_tram.csv", "text/csv")

    # Biểu đồ
    st.line_chart(df.set_index("Thời gian")[["temp", "VPD"]])
    st.dataframe(df.sort_index(ascending=False))
else:
    st.warning("Đang chờ dữ liệu từ MQTT...")
