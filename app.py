import streamlit as st
import pandas as pd
import numpy as np
import paho.mqtt.client as mqtt
import requests
import json
import queue
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# =====================================================================
# CẤU HÌNH GIAO DIỆN & KẾT NỐI
# =====================================================================
st.set_page_config(page_title="Giám Sát Trạm Đơn", page_icon="🌿", layout="centered")
st.title("🌿 Giám Sát Real-Time: Trạm 01")

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "vuon_thong_minh/duy_tran/sensors"
TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

if "mqtt_df" not in st.session_state: st.session_state.mqtt_df = pd.DataFrame()
if "is_running" not in st.session_state: st.session_state.is_running = True

st_autorefresh(interval=30000, key="iot_refresh")

# =====================================================================
# HÀM XỬ LÝ (GIỮ NGUYÊN LOGIC CŨ)
# =====================================================================
def calculate_vpd(temp, humi):
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    return float(np.clip(vp_sat * (1 - (humi / 100)), 0, None))

def send_telegram_auto(message):
    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_TOKEN": return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=2)
    except Exception as e: print(f"Telegram Error: {e}")

def evaluate_status(vpd, temp, humi, low_t, high_t):
    if humi == 0: return "⚠️ Mất tín hiệu", "Độ ẩm bằng 0%", "Kiểm tra giắc cắm"
    if vpd > high_t and temp > 40: return "🔥 BÁO ĐỘNG KHÔ NÓNG", "VPD quá cao + Nóng", "Bật phun sương & lưới lan"
    if vpd < low_t: return "❌ Quá ẩm", f"VPD {vpd:.2f} < {low_t}", "Bật quạt đối lưu"
    return "✅ Môi trường lý tưởng", f"VPD {vpd:.2f} kPa", "Giữ nguyên"

# =====================================================================
# ĐIỀU KHIỂN & CÀI ĐẶT (GIỮ CÁC PRESET)
# =====================================================================
col_start, col_stop = st.columns(2)
with col_start:
    if st.button("▶️ BẮT ĐẦU"): st.session_state.is_running = True
with col_stop:
    if st.button("⏸️ DỪNG"): st.session_state.is_running = False

PLANT_PRESETS = {"Dưa leo": (0.7, 1.3), "Cà chua": (0.6, 1.2), "Ớt chuông": (0.5, 1.0)}
selected = st.selectbox("Cấu hình nhanh:", list(PLANT_PRESETS.keys()))
low_t = st.slider("Ngưỡng thấp (kPa):", 0.1, 1.5, PLANT_PRESETS[selected][0], 0.05)
high_t = st.slider("Ngưỡng cao (kPa):", 1.0, 3.0, PLANT_PRESETS[selected][1], 0.05)

# =====================================================================
# MQTT CLIENT (LUỒNG NỀN)
# =====================================================================
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        userdata.put(pd.DataFrame([data]))
    except: pass

@st.cache_resource
def get_mqtt_queue():
    q = queue.Queue()
    client = mqtt.Client()
    client.user_data_set(q)
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    return q

mqtt_queue = get_mqtt_queue()

# Xử lý dữ liệu đến
while not mqtt_queue.empty():
    new_df = mqtt_queue.get()
    # Tính VPD và Cảnh báo
    t, h = new_df.iloc[0]['Nhiệt độ'], new_df.iloc[0]['Độ ẩm']
    vpd = calculate_vpd(t, h)
    status, reason, action = evaluate_status(vpd, t, h, low_t, high_t)
    
    # Gửi Telegram nếu đang chạy
    if st.session_state.is_running:
        send_telegram_auto(f"Trạm 01: {status}\nVPD: {vpd:.2f} kPa\n{reason}")
    
    # Cập nhật lịch sử
    new_df['VPD'] = vpd
    st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, new_df]).tail(100)

# =====================================================================
# HIỂN THỊ DỮ LIỆU & CSV (GIỮ NGUYÊN)
# =====================================================================
if not st.session_state.mqtt_df.empty:
    st.download_button("📥 Tải lịch sử CSV", st.session_state.mqtt_df.to_csv(index=False), "log.csv")
    st.dataframe(st.session_state.mqtt_df, use_container_width=True)
    
    # Biểu đồ
    fig = px.line(st.session_state.mqtt_df, x="Thời gian", y="VPD", title="Chỉ số VPD Trạm 01")
    fig.add_hline(y=low_t, line_dash="dash", line_color="blue")
    fig.add_hline(y=high_t, line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Đang chờ dữ liệu từ MQTT...")
