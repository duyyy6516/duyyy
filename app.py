import streamlit as pd
import pandas as pd
import random
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
st.markdown("Mô phỏng: **Mỗi trạm gửi cách nhau 150s, các trạm lệch pha nhau đúng 30s**.")

# =====================================================================
# KHỞI TẠO SESSION STATE
# =====================================================================
if "mqtt_df" not in st.session_state:
    st.session_state.mqtt_df = pd.DataFrame(columns=["Thời gian", "STT", "Nhiệt độ", "Độ ẩm", "VPD (kPa)", "Trạng thái"])

if "is_running" not in st.session_state:
    st.session_state.is_running = True

if "current_station_index" not in st.session_state:
    st.session_state.current_station_index = 0

if "slider_low" not in st.session_state:
    st.session_state.slider_low = 0.45

if "slider_high" not in st.session_state:
    st.session_state.slider_high = 1.70

if "plant_selector" not in st.session_state:
    st.session_state.plant_selector = "Tự tùy chỉnh (Kéo tay)"

STATIONS_LIST = ["1", "2", "3", "4", "5"]

# =====================================================================
# AUTO REFRESH (Xử lý sự kiện kích hoạt theo chu kỳ)
# =====================================================================
refresh_counter = None
if st.session_state.is_running:
    refresh_counter = st_autorefresh(interval=30000, key="iot_refresh")

if "last_refresh_counter" not in st.session_state:
    st.session_state.last_refresh_counter = 0

# =====================================================================
# NÚT ĐIỀU KHIỂN HỆ THỐNG
# =====================================================================
st.subheader("🎮 Bộ Điều Khiển Hệ Thống")
col_start, col_stop = st.columns(2)

with col_start:
    if st.button("▶️ BẮT ĐẦU (Chạy tự động)", use_container_width=True, type="primary"):
        st.session_state.is_running = True
        st.rerun()

with col_stop:
    if st.button("⏸️ DỪNG LẠI (Tạm dừng quét)", use_container_width=True):
        st.session_state.is_running = False
        st.rerun()

if st.session_state.is_running:
    st.success("🤖 Hệ thống đang: **CHẠY TỰ ĐỘNG (Xung nhịp 30s chuẩn)**")
else:
    st.warning("⏸️ Hệ thống đang: **TẠM DỪNG QUÉT**")

# =====================================================================
# CÀI ĐẶT NGƯỠNG VPD & CÂY TRỒNG
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

def on_plant_change():
    selected = st.session_state.plant_selector
    if selected != "Tự tùy chỉnh (Kéo tay)":
        st.session_state.slider_low = PLANT_PRESETS[selected][0]
        st.session_state.slider_high = PLANT_PRESETS[selected][1]

selected_plant = st.radio(
    "🌱 Chọn cấu hình cây trồng:",
    options=list(PLANT_PRESETS.keys()),
    key="plant_selector",
    on_change=on_plant_change
)

low_threshold = st.slider(
    "1️⃣ Ngưỡng VPD thấp (Quá ẩm)",
    min_value=0.1, max_value=1.5, step=0.05,
    format="%.2f kPa", key="slider_low"
)

high_threshold = st.slider(
    "2️⃣ Ngưỡng VPD cao (Khô nóng)",
    min_value=1.0, max_value=3.0, step=0.05,
    format="%.2f kPa", key="slider_high"
)

# =====================================================================
# LOGIC TÍNH TOÁN & ĐÁNH GIÁ VPD (Sử dụng hàm toán học thuần túy)
# =====================================================================
def calculate_vpd(temp, humi):
    # Tính áp suất hơi bão hòa (SVP) bằng công thức thuần Python thay cho numpy
    import math
    vp_sat = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    vpd = vp_sat * (1 - (humi / 100))
    return max(0.0, vpd) # Giới hạn không cho âm dưới 0

def evaluate_status(vpd, humi, low, high):
    if humi == 0: return "🔌 Mất tín hiệu"
    if vpd < low: return "❌ Quá ẩm"
    if vpd > high: return "❌ Khô nóng"
    return "✅ Bình thường"

# =====================================================================
# XỬ LÝ DỮ LIỆU KHI ĐẾN CHU KỲ REFRESH
# =====================================================================
idx = st.session_state.current_station_index
active_station = STATIONS_LIST[idx]
next_station = STATIONS_LIST[(idx + 1) % len(STATIONS_LIST)]

if st.session_state.is_running and refresh_counter is not None and refresh_counter != st.session_state.last_refresh_counter:
    
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    temp = round(random.uniform(25, 40), 1)
    humi = round(random.uniform(40, 90), 1)
    vpd_val = round(calculate_vpd(temp, humi), 3)
    
    status = evaluate_status(vpd_val, humi, low_threshold, high_threshold)

    new_row = pd.DataFrame([{
        "Thời gian": current_time_str,
        "STT": active_station,
        "Nhiệt độ": temp,
        "Độ ẩm": humi,
        "VPD (kPa)": vpd_val,
        "Trạng thái": status
    }])

    st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, new_row], ignore_index=True).tail(100)
    
    st.session_state.current_station_index = (idx + 1) % len(STATIONS_LIST)
    st.session_state.last_refresh_counter = refresh_counter
    st.rerun()

# =====================================================================
# HIỂN THỊ MONITORING TRÊN GIAO DIỆN
# =====================================================================
st.subheader("⏱️ Tiến Độ Điều Phối Xung Nhịp")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="🟢 Trạm vừa xử lý dữ liệu", value=f"Trạm {active_station}")
with col2:
    st.metric(label="⏳ Trạm kế tiếp", value=f"Trạm {next_station}")

st.subheader("📋 Bảng Dữ Liệu Realtime")
if not st.session_state.mqtt_df.empty:
    st.dataframe(st.session_state.mqtt_df, use_container_width=True)
else:
    st.info("Đang chờ chu kỳ quét đầu tiên của hệ thống tự động (30 giây)...")
