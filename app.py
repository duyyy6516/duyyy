import streamlit as st
import pandas as pd
import numpy as np
import random
import streamlit.components.v1 as components
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Cấu hình
st.set_page_config(page_title="Hệ Thống Quét Điều Khiển", page_icon="🌿", layout="centered")
st.title("🌿 Giám Sát Real-Time: Trạm 01")

# Khởi tạo trạng thái
if "mqtt_df" not in st.session_state: st.session_state.mqtt_df = pd.DataFrame()
if "is_running" not in st.session_state: st.session_state.is_running = False

# Hàm logic tính toán
def calculate_vpd(temp, humi):
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    return float(np.clip(vp_sat * (1 - (humi / 100)), 0, None))

# Bộ điều khiển
st.subheader("⚙️ Bộ Điều Khiển Hệ Thống")
col_start, col_stop = st.columns(2)

if col_start.button("▶️ BẮT ĐẦU", type="primary"):
    st.session_state.is_running = True
    # Chạy lần đầu ngay khi bấm
    st.rerun()

if col_stop.button("⏸️ DỪNG LẠI"):
    st.session_state.is_running = False
    st.rerun()

# --- CHỈ CHẠY LOGIC KHI ĐÃ BẤM BẮT ĐẦU ---
if st.session_state.is_running:
    # 1. Kích hoạt tự làm mới trang sau mỗi 30s
    st_autorefresh(interval=30000, key="iot_refresh")
    
    # 2. Tạo dữ liệu
    temp = round(random.uniform(25.0, 35.0), 1)
    humi = round(random.uniform(50.0, 85.0), 1)
    time_log = datetime.now().strftime("%H:%M:%S")
    vpd = calculate_vpd(temp, humi)
    
    new_row = pd.DataFrame([{"Thời gian": time_log, "Nhiệt độ": temp, "Độ ẩm": humi, "VPD": vpd}])
    st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, new_row]).tail(100)
    
    st.success("✅ Hệ thống đang chạy - Đang cập nhật dữ liệu...")

    # 3. Bộ đếm ngược hiển thị trên giao diện
    countdown_html = """
    <div style="background-color: #e8f4f9; padding: 10px; border-radius: 8px; border-left: 5px solid #007bff; margin-bottom: 10px;">
        ⏱️ <b>Chu kỳ quét:</b> <span id="timer" style="color: #d9534f; font-weight: bold;">30</span> giây nữa cập nhật lần kế tiếp.
    </div>
    <script>
        var timeLeft = 30;
        var timerElement = document.getElementById('timer');
        var countdown = setInterval(function() {
            timeLeft--;
            if(timeLeft <= 0) { clearInterval(countdown); }
            else { timerElement.innerText = timeLeft; }
        }, 1000);
    </script>
    """
    components.html(countdown_html, height=60)

else:
    st.warning("⏸️ Hệ thống đang TẠM DỪNG. Nhấn nút [BẮT ĐẦU] để khởi động trạm.")

# Hiển thị dữ liệu (Luôn hiển thị nếu đã có dữ liệu từ trước)
if not st.session_state.mqtt_df.empty:
    st.dataframe(st.session_state.mqtt_df.sort_index(ascending=False), use_container_width=True)
    fig = px.line(st.session_state.mqtt_df, x="Thời gian", y="VPD", title="Biểu đồ VPD")
    st.plotly_chart(fig, use_container_width=True)
