import streamlit as st
import pandas as pd
import numpy as np
import paho.mqtt.client as mqtt
import requests
import json
import random
import queue
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# =====================================================================
# CẤU HÌNH
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

# Tự động làm mới mỗi 30s
st_autorefresh(interval=30000, key="iot_refresh")

# =====================================================================
# CÁC HÀM XỬ LÝ (GIỮ NGUYÊN)
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
    if vpd > high_t: return "❌ Khô nóng", f"VPD {vpd:.2f} cao", "Bật phun sương"
    if vpd < low_t: return "❌ Quá ẩm", f"VPD {vpd:.2f} thấp", "Bật quạt đối lưu"
    return "✅ Lý tưởng", f"VPD {vpd:.2f} ổn định", "Giữ nguyên"

# =====================================================================
# UI ĐIỀU KHIỂN & CÀI ĐẶT
# =====================================================================
col1, col2 = st.columns(2)
with col1:
    if st.button("▶️ BẮT ĐẦU"): st.session_state.is_running = True
with col2:
    if st.button("⏸️ DỪNG"): st.session_state.is_running = False

PLANT_PRESETS = {"Dưa leo": (0.7, 1.3), "Cà chua": (0.6, 1.2), "Ớt chuông": (0.5, 1.0)}
selected = st.selectbox("Cấu hình nhanh:", list(PLANT_PRESETS.keys()))
low_t = st.slider("Ngưỡng thấp (kPa):", 0.1, 1.5, PLANT_PRESETS[selected][0], 0.05)
high_t = st.slider("Ngưỡng cao (kPa):", 1.0, 3.0, PLANT_PRESETS[selected][1], 0.05)

# =====================================================================
# LOGIC MQTT & RANDOM MÔ PHỎNG
# =====================================================================
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        userdata.put(pd.DataFrame([data]))
    except: pass

@st.cache_resource
def start_mqtt():
    q = queue.Queue()
    client = mqtt.Client()
    client.user_data_set(q)
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    return q

mqtt_queue = start_mqtt()

# Xử lý dữ liệu (Ưu tiên MQTT, nếu không có MQTT thì Random)
if not mqtt_queue.empty():
    df_new = mqtt_queue.get()
else:
    # --- ĐÂY LÀ PHẦN RANDOM MÔ PHỎNG BẠN CẦN ---
    if st.session_state.is_running:
        temp = round(random.uniform(25.0, 35.0), 1)
        humi = round(random.uniform(50.0, 85.0), 1)
        df_new = pd.DataFrame([{
            "Thời gian": datetime.now().strftime("%H:%M:%S"),
            "Nhiệt độ": temp,
            "Độ ẩm": humi
        }])
    else:
        df_new = pd.DataFrame()

if not df_new.empty:
    t, h = df_new.iloc[0]['Nhiệt độ'], df_new.iloc[0]['Độ ẩm']
    vpd = calculate_vpd(t, h)
    status, reason, action = evaluate_status(vpd, t, h, low_t, high_t)
    
    if st.session_state.is_running:
        send_telegram_auto(f"Trạm 01: {status}\nVPD: {vpd:.2f} kPa")
    
    df_new['VPD'] = vpd
    df_new['Trạng thái'] = status
    st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, df_new]).tail(50)

# =====================================================================
# HIỂN THỊ
# =====================================================================
if not st.session_state.mqtt_df.empty:
    st.download_button("📥 Tải CSV", st.session_state.mqtt_df.to_csv(index=False), "log.csv")
    st.dataframe(st.session_state.mqtt_df.sort_index(ascending=False), use_container_width=True)
    
    fig = px.line(st.session_state.mqtt_df, x="Thời gian", y="VPD", title="Chỉ số VPD")
    fig.add_hline(y=low_t, line_dash="dash", line_color="blue")
    fig.add_hline(y=high_t, line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)
