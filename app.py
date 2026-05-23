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
st.title("🌿 Giám Sát Real-Time: 5 Trạm")

# Khởi tạo trạng thái
if "mqtt_df" not in st.session_state: st.session_state.mqtt_df = pd.DataFrame()
if "is_running" not in st.session_state: st.session_state.is_running = False
if "current_station" not in st.session_state: st.session_state.current_station = 1

# Bộ điều khiển
col_start, col_stop = st.columns(2)
if col_start.button("▶️ BẮT ĐẦU", type="primary"):
    st.session_state.is_running = True
    st.rerun()
if col_stop.button("⏸️ DỪNG LẠI"):
    st.session_state.is_running = False
    st.rerun()

# Logic xử lý chính
if st.session_state.is_running:
    # 1. Tự làm mới mỗi 30s
    st_autorefresh(interval=30000, key="iot_refresh")
    
    # 2. Tạo dữ liệu cho trạm hiện tại
    st_id = st.session_state.current_station
    temp = round(random.uniform(25.0, 35.0), 1)
    humi = round(random.uniform(50.0, 85.0), 1)
    
    # 3. Lưu vào DataFrame
    new_row = pd.DataFrame([{
        "Thời gian": datetime.now().strftime("%H:%M:%S"), 
        "STT": str(st_id), # Đã fix: Lấy đúng số trạm hiện tại
        "Nhiệt độ": temp, 
        "Độ ẩm": humi
    }])
    st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, new_row]).tail(100)
    
    # 4. Tăng trạm cho lần sau (vòng lặp 1-5)
    st.session_state.current_station = (st_id % 5) + 1
    
    st.success(f"✅ Đang quét: Trạm {st_id}")
    
    # Bộ đếm ngược
    components.html("""
    <div style="background:#e8f4f9; padding:10px; border-radius:5px;">
        ⏱️ Giây kế tiếp quét trạm mới: <span id="t">30</span>
    </div>
    <script>
        let s = 30;
        setInterval(() => { s = s > 0 ? s - 1 : 30; document.getElementById('t').innerText = s; }, 1000);
    </script>
    """, height=50)
else:
    st.warning("⏸️ Hệ thống đang dừng.")

# Hiển thị dữ liệu
if not st.session_state.mqtt_df.empty:
    st.dataframe(st.session_state.mqtt_df.sort_index(ascending=False), use_container_width=True)
