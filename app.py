import streamlit as st
import random
import math
from datetime import datetime
import pandas as pd

# Cấu hình trang web Streamlit
st.set_page_config(page_title="Hệ thống VPD điều khiển", page_icon="🌿", layout="centered")

st.title("Hệ Thống Giám Sát & Tính Toán VPD 🌿")

# --- CÔNG THỨC TÍNH VPD ---
def calculate_vpd(temp, rh):
    vp_sat = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    vpd = vp_sat * (1.0 - (rh / 100.0))
    return vpd

# --- KHỞI TẠO BIẾN TRONG SESSION STATE ---
if 'temp' not in st.session_state:
    st.session_state.temp = 31.5
if 'rh' not in st.session_state:
    st.session_state.rh = 56.5
if 'countdown' not in st.session_state:
    st.session_state.countdown = 30  
if 'last_updated' not in st.session_state:
    st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")
if 'stt_counter' not in st.session_state:
    st.session_state.stt_counter = 1

# Biến kiểm tra hệ thống có đang chạy hay không (Mặc định ban đầu là False - dừng)
if 'is_running' not in st.session_state:
    st.session_state.is_running = False

# Khởi tạo danh sách lưu lịch sử dữ liệu
if 'history' not in st.session_state:
    first_vpd = calculate_vpd(st.session_state.temp, st.session_state.rh)
    st.session_state.history = [{
        "STT": st.session_state.stt_counter,
        "Thời gian": st.session_state.last_updated,
        "Nhiệt độ (°C)": st.session_state.temp,
        "Độ ẩm (%)": st.session_state.rh,
        "VPD (kPa)": round(first_vpd, 2)
    }]

# --- HÀM THỰC HIỆN RANDOM VÀ GHI VÀO LỊCH SỬ ---
def trigger_new_data():
    st.session_state.temp = round(random.uniform(15.0, 38.0), 1)
    st.session_state.rh = round(random.uniform(30.0, 95.0), 1)
    st.session_state.countdown = 30 
    st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")
    st.session_state.stt_counter += 1
    
    new_vpd = calculate_vpd(st.session_state.temp, st.session_state.rh)
    new_record = {
        "STT": st.session_state.stt_counter,
        "Thời gian": st.session_state.last_updated,
        "Nhiệt độ (°C)": st.session_state.temp,
        "Độ ẩm (%)": st.session_state.rh,
        "VPD (kPa)": round(new_vpd, 2)
    }
    st.session_state.history.insert(0, new_record)

# --- KHU VỰC ĐIỀU KHIỂN (BẮT ĐẦU / TẠM DỪNG) ---
st.write("### 🎛️ Bảng Điều Khiển")
col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("▶️ Bắt đầu chạy tự động", type="primary", disabled=st.session_state.is_running):
        st.session_state.is_running = True
        st.rerun()

with col_btn2:
    if st.button("⏸️ Tạm dừng hệ thống", type="secondary", disabled=not st.session_state.is_running):
        st.session_state.is_running = False
        st.rerun()

st.write("---")

# --- ĐOẠN CODE CHẠY LẠI MỖI 1 GIÂY ---
run_interval = 1 if st.session_state.is_running else 999999

@st.fragment(run_every=run_interval)
def vpd_controlled_monitor():
    # 1. Xử lý giảm số giây đếm ngược nếu trạng thái đang bật
    if st.session_state.is_running:
        st.session_state.countdown -= 1
        if st.session_state.countdown < 0:
            trigger_new_data()
            
    # 2. HIỂN THỊ TRẠNG THÁI & ĐỒNG HỒ ĐẾM NGƯỢC
    if st.session_state.is_running:
        st.success("🟢 Hệ thống đang HOẠT ĐỘNG tự động")
        st.write(f"### ⏳ Tự động đổi số sau: **{st.session_state.countdown}** giây")
        st.progress(st.session_state.countdown / 30)
    else:
        st.error("🔴 Hệ thống đang TẠM DỪNG (Hãy bấm Bắt đầu ở trên để chạy)")
        st.write("### ⏳ Đang chờ kích hoạt...")
        st.progress(1.0)
        
    st.caption(f"🔄 Dữ liệu cập nhật gần nhất: {st.session_state.last_updated} (Lần thứ: {st.session_state.stt_counter})")
    st.write("---")

    # 3. HIỂN THỊ THÔNG SỐ CƠ BẢN
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="🌡️ Nhiệt độ hiện tại", value=f"{st.session_state.temp} °C")
    with col2:
        st.metric(label="💧 Độ ẩm hiện tại", value=f"{st.session_state.rh} %")
        
    vpd_result = calculate_vpd(st.session_state.temp, st.session_state.rh)
    
    st.write("---")
    st.subheader("Chỉ số VPD hiện tại:")
    st.metric(label="Áp suất hơi thâm hụt (Vapor Pressure Deficit)", value=f"{vpd_result:.2f} kPa")
    
    # 4. ĐÁNH GIÁ MÔI TRƯỜNG DỰA TRÊN VPD
    if vpd_result < 0.4:
        st.warning("⚠️ **VPD quá thấp (Môi trường quá ẩm):** Cây khó thoát nước.")
    elif 0.4 <= vpd_result <= 0.8:
        st.info("🌱 **VPD Thấp:** Phù hợp cho giai đoạn nhân giống, kích rễ.")
    elif 0.8 < vpd_result <= 1.2:
        st.success("✅ **VPD Lý tưởng:** Môi trường hoàn hảo.")
    elif 1.2 < vpd_result <= 1.6:
        st.info("🍂 **VPD Hơi cao:** Phù hợp cho giai đoạn ra hoa.")
    else:
        st.error("🚨 **VPD quá cao (Môi trường quá khô):** Cây mất nước nhanh.")

    # Nút bấm đổi số khẩn cấp bằng tay
    if st.button("🎲 Random Thủ Công (1 lần)", type="secondary"):
        trigger_new_data()
        st.rerun()

    # --- 5. HIỂN THỊ LỊCH SỬ DỮ LIỆU ---
    st.write("
