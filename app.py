import streamlit as st
import pandas as pd
import numpy as np
import requests
import random
import streamlit.components.v1 as components
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# =====================================================================
# CẤU HÌNH GIAO DIỆN
# =====================================================================
st.set_page_config(page_title="Hệ Thống Quét Điều Khiển", page_icon="🌿", layout="centered")
st.title("🌿 Giám Sát Real-Time: Trạm 01")

# --- KHỞI TẠO STATE ---
if "mqtt_df" not in st.session_state: st.session_state.mqtt_df = pd.DataFrame()
# Mặc định là False để KHÔNG chạy khi mới load web
if "is_running" not in st.session_state: st.session_state.is_running = False 

# =====================================================================
# BỘ ĐIỀU KHIỂN BẮT ĐẦU / DỪNG
# =====================================================================
st.subheader("⚙️ Bộ Điều Khiển Hệ Thống")
col_start, col_stop = st.columns(2)

if col_start.button("▶️ BẮT ĐẦU", type="primary"):
    st.session_state.is_running = True
    st.rerun()

if col_stop.button("⏸️ DỪNG LẠI"):
    st.session_state.is_running = False
    st.rerun()

# Chỉ kích hoạt autorefresh khi is_running = True
if st.session_state.is_running:
    st_autorefresh(interval=30000, key="iot_refresh")
    st.success("✅ Hệ thống đang CHẠY")
else:
    st.warning("⏸️ Hệ thống đang DỪNG. Nhấn Bắt đầu để quét.")

# =====================================================================
# CÁC HÀM XỬ LÝ
# =====================================================================
def calculate_vpd(temp, humi):
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    return float(np.clip(vp_sat * (1 - (humi / 100)), 0, None))

# =====================================================================
# LOGIC CHỈ CHẠY KHI ĐÃ BẤM NÚT
# =====================================================================
if st.session_state.is_running:
    # 1. Tạo dữ liệu random (Mô phỏng)
    temp = round(random.uniform(25.0, 35.0), 1)
    humi = round(random.uniform(50.0, 85.0), 1)
    time_log = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    vpd = calculate_vpd(temp, humi)
    
    # 2. Lưu vào DataFrame
    new_row = pd.DataFrame([{"Thời gian": time_log, "Nhiệt độ": temp, "Độ ẩm": humi, "VPD": vpd}])
    st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, new_row]).tail(100)

    # 3. Hiển thị bộ đếm ngược 30s
    countdown_html = """
    <div style="background-color: #f0f2f6; padding: 12px; border-radius: 8px; border-left: 5px solid #1f77b4; margin: 10px 0;">
        <span style="font-weight: bold;">⏱️ CHU KỲ QUÉT:</span> 
        <span id="timer" style="color: #ff4b4b; font-weight: bold;">30</span> giây nữa sẽ cập nhật...
    </div>
    <script>
        let t = 30;
        setInterval(() => { t = t > 0 ? t - 1 : 30; document.getElementById('timer').innerText = t; }, 1000);
    </script>
    """
    components.html(countdown_html, height=60)

# =====================================================================
# HIỂN THỊ DỮ LIỆU
# =====================================================================
if not st.session_state.mqtt_df.empty:
    st.dataframe(st.session_state.mqtt_df.sort_index(ascending=False), use_container_width=True)
    
    fig = px.line(st.session_state.mqtt_df, x="Thời gian", y="VPD", title="Chỉ số VPD Trạm 01")
    st.plotly_chart(fig, use_container_width=True)
