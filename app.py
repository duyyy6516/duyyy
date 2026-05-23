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
# CẤU HÌNH GIAO DIỆN
# =====================================================================
st.set_page_config(page_title="Hệ Thống Quét Điều Khiển", page_icon="🌿", layout="centered")

st.title("🌿 Giám Sát Real-Time: Trạm 01")
st.markdown("Mô phỏng: **Dữ liệu cập nhật mỗi 30s**.")

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "vuon_thong_minh/duy_tran/sensors"
TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN" 
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

if "mqtt_df" not in st.session_state: st.session_state.mqtt_df = pd.DataFrame()
if "is_running" not in st.session_state: st.session_state.is_running = False

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
    if vpd < low_t: return "❌ Quá ẩm", f"VPD {vpd:.2f} < {low_t}", "Bật quạt đối lưu"
    if vpd > high_t: return "❌ Khô hanh", f"VPD {vpd:.2f} > {high_t}", "Bật phun sương"
    return "✅ Môi trường lý tưởng", f"VPD {vpd:.2f} ổn định", "Giữ nguyên"

# =====================================================================
# ĐIỀU KHIỂN & CÀI ĐẶT
# =====================================================================
st.subheader("⚙️ Bộ Điều Khiển Hệ Thống")
col_start, col_stop = st.columns(2)
if col_start.button("▶️ BẮT ĐẦU", use_container_width=True, type="primary"):
    st.session_state.is_running = True
    st.rerun()
if col_stop.button("⏸️ DỪNG LẠI", use_container_width=True):
    st.session_state.is_running = False
    st.rerun()

# Cài đặt ngưỡng
PLANT_PRESETS = {"Tự tùy chỉnh": None, "🥒 Dưa leo": (0.7, 1.3), "🍅 Cà chua": (0.6, 1.2)}
st.selectbox("🌿 Cấu hình nhanh:", options=list(PLANT_PRESETS.keys()), key="plant_selector")
low_threshold = st.slider("Ngưỡng VPD Thấp:", 0.1, 1.5, 0.45, key="slider_low")
high_threshold = st.slider("Ngưỡng VPD Cao:", 1.0, 3.0, 1.70, key="slider_high")

# =====================================================================
# LOGIC CHẠY KHI ĐÃ BẤM NÚT
# =====================================================================
if st.session_state.is_running:
    st_autorefresh(interval=30000, key="iot_refresh")
    
    # Tạo dữ liệu
    temp = round(random.uniform(25.0, 35.0), 1)
    humi = round(random.uniform(50.0, 85.0), 1)
    time_log = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    vpd = calculate_vpd(temp, humi)
    status, reason, action = evaluate_status(vpd, temp, humi, low_threshold, high_threshold)
    
    # Lưu dữ liệu
    new_row = pd.DataFrame([{"Thời gian": time_log, "STT": "01", "Nhiệt độ": temp, "Độ ẩm": humi, "VPD": vpd, "Trạng thái": status}])
    st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, new_row]).tail(100)
    
    send_telegram_auto(f"Trạm 01: {status}\nVPD: {vpd:.2f} kPa\n{reason}")

    # Đếm ngược UI
    components.html("""<div style="background:#f0f2f6; padding:10px; border-radius:5px; border-left:5px solid #1f77b4;">
        ⏱️ <b>ĐỒNG HỒ QUÉT:</b> <span id="timer" style="color:#ff4b4b; font-weight:bold;">30</span> giây nữa...
    </div><script>let t=30; setInterval(()=>{t=t>0?t-1:30; document.getElementById('timer').innerText=t;}, 1000);</script>""", height=60)
else:
    st.warning("⏸️ Hệ thống đang TẠM DỪNG. Nhấn BẮT ĐẦU để kích hoạt.")

# =====================================================================
# HIỂN THỊ
# =====================================================================
if not st.session_state.mqtt_df.empty:
    st.download_button("📥 Tải CSV", st.session_state.mqtt_df.to_csv(index=False), "data_01.csv", use_container_width=True)
    st.dataframe(st.session_state.mqtt_df.sort_index(ascending=False), use_container_width=True)
    
    fig = px.line(st.session_state.mqtt_df, x="Thời gian", y="VPD", title="Chỉ số VPD Trạm 01")
    fig.add_hline(y=low_threshold, line_dash="dash", line_color="blue")
    fig.add_hline(y=high_threshold, line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)
