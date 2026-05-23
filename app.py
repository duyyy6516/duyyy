import streamlit as st
import pandas as pd
import numpy as np
import paho.mqtt.client as mqtt
import requests
import json
import random
import streamlit.components.v1 as components
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# =====================================================================
# CẤU HÌNH GIAO DIỆN DI ĐỘNG
# =====================================================================

st.set_page_config(
    page_title="Hệ Thống Quét Điều Khiển",
    page_icon="🚨",
    layout="centered"
)

st.title("🚨 Giám Sát Real-Time Quét Vòng 5 Trạm")

st.markdown(
    "Mô phỏng: **Mỗi trạm gửi cách nhau 150s, các trạm lệch pha nhau đúng 30s**."
)

# =====================================================================
# CẤU HÌNH MQTT + TELEGRAM
# =====================================================================

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "vuon_thong_minh/duy_tran/sensors"

TELEGRAM_TOKEN = "YOUR_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

# =====================================================================
# KHỞI TẠO SESSION STATE
# =====================================================================

if "mqtt_df" not in st.session_state:
    st.session_state.mqtt_df = pd.DataFrame()

if "is_running" not in st.session_state:
    st.session_state.is_running = True

if "current_station_index" not in st.session_state:
    st.session_state.current_station_index = 0

if "last_processed_idx" not in st.session_state:
    st.session_state.last_processed_idx = -1

# =====================================================================
# DANH SÁCH TRẠM
# =====================================================================

STATIONS_LIST = ["1", "2", "3", "4", "5"]

# =====================================================================
# AUTO REFRESH
# =====================================================================

if st.session_state.is_running:
    st_autorefresh(interval=30000, key="iot_refresh")

# =====================================================================
# NÚT ĐIỀU KHIỂN
# =====================================================================

st.subheader("🎮 Bộ Điều Khiển Hệ Thống")

col_start, col_stop = st.columns(2)

with col_start:

    if st.button(
        "▶️ BẮT ĐẦU (Chạy tự động)",
        use_container_width=True,
        type="primary"
    ):

        st.session_state.is_running = True
        st.session_state.last_processed_idx = -1
        st.rerun()

with col_stop:

    if st.button(
        "⏸️ DỪNG LẠI (Tạm dừng quét)",
        use_container_width=True
    ):

        st.session_state.is_running = False
        st.rerun()

if st.session_state.is_running:

    st.success(
        "🤖 Hệ thống đang: **CHẠY TỰ ĐỘNG (Xung nhịp 30s chuẩn)**"
    )

else:

    st.warning(
        "⏸️ Hệ thống đang: **TẠM DỪNG QUÉT**"
    )

# =====================================================================
# CÀI ĐẶT NGƯỠNG VPD
# =====================================================================

st.subheader("⚙️ Cài Đặt Ngưỡng VPD")

PLANT_PRESETS = {
    "Tự tùy chỉnh (Kéo tay)": None,
    "🥒 Dưa leo (Nhà kính)": (0.70, 1.30),
    "🍓 Dâu tây (New Zealand, Nhật)": (0.40, 0.80),
    "🍅 Cà chua (Beef, Cherry)": (0.60, 1.20),
    "🫑 Ớt chuông": (0.50, 1.00),
    "🥬 Rau ăn lá (Xà lách)": (0.40, 0.85),
    "🌹 Hoa hồng cắt cành": (0.80, 1.20)
}

# =====================================================================
# KHỞI TẠO GIÁ TRỊ MẶC ĐỊNH
# =====================================================================

if "slider_low" not in st.session_state:
    st.session_state.slider_low = 0.45

if "slider_high" not in st.session_state:
    st.session_state.slider_high = 1.70

if "plant_selector" not in st.session_state:
    st.session_state.plant_selector = "Tự tùy chỉnh (Kéo tay)"

# =====================================================================
# TỰ ĐỘNG ĐỔI NGƯỠNG KHI CHỌN CÂY
# =====================================================================

def on_plant_change():

    selected_plant = st.session_state.plant_selector

    if selected_plant != "Tự tùy chỉnh (Kéo tay)":

        st.session_state.slider_low = PLANT_PRESETS[selected_plant][0]

        st.session_state.slider_high = PLANT_PRESETS[selected_plant][1]

# =====================================================================
# CHỌN LOẠI CÂY
# =====================================================================

st.markdown("## 🌱 Chọn cấu hình cây trồng")

selected_plant = st.radio(
    "Danh sách loại cây:",
    options=list(PLANT_PRESETS.keys()),
    key="plant_selector",
    on_change=on_plant_change
)

# =====================================================================
# HIỂN THỊ FULL DANH SÁCH CÂY
# =====================================================================

st.markdown("## 📋 Bảng ngưỡng VPD đề xuất")

for plant, value in PLANT_PRESETS.items():

    checked = "✅" if plant == selected_plant else "⬜"

    if value is None:

        bg_color = "#d1ecf1" if plant == selected_plant else "#f8f9fa"

        border_color = "#17a2b8" if plant == selected_plant else "#cccccc"

        st.markdown(
            f"""
            <div style="
                padding:14px;
                border-radius:14px;
                margin-bottom:12px;
                background-color:{bg_color};
                border-left:7px solid {border_color};
            ">

                <div style="
                    font-size:17px;
                    font-weight:bold;
                    margin-bottom:6px;
                ">
                    {checked} {plant}
                </div>

                <div style="
                    font-size:14px;
                    color:#444;
                ">
                    Người dùng tự điều chỉnh ngưỡng bằng slider.
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        low, high = value

        bg_color = "#d4edda" if plant == selected_plant else "#f8f9fa"

        border_color = "#28a745" if plant == selected_plant else "#cccccc"

        st.markdown(
            f"""
            <div style="
                padding:14px;
                border-radius:14px;
                margin-bottom:12px;
                background-color:{bg_color};
                border-left:7px solid {border_color};
            ">

                <div style="
                    font-size:17px;
                    font-weight:bold;
                    margin-bottom:8px;
                ">
                    {checked} {plant}
                </div>

                <div style="
                    font-size:15px;
                    margin-bottom:4px;
                ">
                    🌡️ VPD tối ưu:
                    <b>{low:.2f} → {high:.2f} kPa</b>
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

# =====================================================================
# SLIDER NGƯỠNG
# =====================================================================

low_threshold = st.slider(
    "1️⃣ Ngưỡng VPD thấp (Quá ẩm)",
    min_value=0.1,
    max_value=1.5,
    step=0.05,
    format="%.2f kPa",
    key="slider_low"
)

high_threshold = st.slider(
    "2️⃣ Ngưỡng VPD cao (Khô nóng)",
    min_value=1.0,
    max_value=3.0,
    step=0.05,
    format="%.2f kPa",
    key="slider_high"
)

st.session_state.low_threshold = low_threshold
st.session_state.high_threshold = high_threshold

# =====================================================================
# HÀM TÍNH VPD
# =====================================================================

def calculate_vpd(temp, humi):

    vp_sat = 0.61078 * np.exp(
        (17.27 * temp) / (temp + 237.3)
    )

    return float(
        np.clip(
            vp_sat * (1 - (humi / 100)),
            0,
            None
        )
    )

# =====================================================================
# HÀM ĐÁNH GIÁ
# =====================================================================

def evaluate_status(vpd, temp, humi):

    if humi == 0:
        return "🔌 Mất tín hiệu"

    if vpd < low_threshold:
        return "❌ Quá ẩm"

    elif vpd > high_threshold:
        return "❌ Khô nóng"

    else:
        return "✅ Bình thường"

# =====================================================================
# MÔ PHỎNG REALTIME
# =====================================================================

st.subheader("⏱️ Tiến Độ Điều Phối Xung Nhịp")

idx = st.session_state.current_station_index

active_station = STATIONS_LIST[idx]

next_station = STATIONS_LIST[
    (idx + 1) % len(STATIONS_LIST)
]

col1, col2 = st.columns(2)

with col1:

    st.metric(
        label="🟢 Trạm vừa xử lý dữ liệu",
        value=f"Trạm {active_station}"
    )

with col2:

    st.metric(
        label="⏳ Trạm kế tiếp",
        value=f"Trạm {next_station}"
    )

# =====================================================================
# TẠO DỮ LIỆU GIẢ
# =====================================================================

if (
    st.session_state.is_running
    and
    st.session_state.last_processed_idx != idx
):

    current_time_str = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    temp = round(random.uniform(25, 40), 1)

    humi = round(random.uniform(40, 90), 1)

    vpd_val = round(
        calculate_vpd(temp, humi),
        3
    )

    status = evaluate_status(vpd_val, temp, humi)

    new_row = pd.DataFrame([{
        "Thời gian": current_time_str,
        "STT": active_station,
        "Nhiệt độ": temp,
        "Độ ẩm": humi,
        "VPD (kPa)": vpd_val,
        "Trạng thái": status
    }])

    if st.session_state.mqtt_df.empty:

        st.session_state.mqtt_df = new_row

    else:

        st.session_state.mqtt_df = pd.concat(
            [
                st.session_state.mqtt_df,
                new_row
            ],
            ignore_index=True
        ).tail(100)

    st.session_state.last_processed_idx = idx

    st.session_state.current_station_index = (
        idx + 1
    ) % len(STATIONS_LIST)

# =====================================================================
# BẢNG DỮ LIỆU
# =====================================================================

st.subheader("📋 Bảng Dữ Liệu Realtime")

st.dataframe(
    st.session_state.mqtt_df,
    use_container_width=True
)

# =====================================================================
# BIỂU ĐỒ
# =====================================================================

st.subheader("📈 Biểu Đồ Realtime")

chart_df = st.session_state.mqtt_df.copy()

if not chart_df.empty:

    chart_df["Thời gian"] = pd.to_datetime(
        chart_df["Thời gian"]
    )

    fig = px.line(
        chart_df,
        x="Thời gian",
        y="VPD (kPa)",
        color="STT",
        markers=True,
        title="Biểu đồ VPD Realtime"
    )

    fig.add_hline(
        y=low_threshold,
        line_dash="dash"
    )

    fig.add_hline(
        y=high_threshold,
        line_dash="dash"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )
