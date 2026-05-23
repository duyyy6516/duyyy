import streamlit as st
import random
import math
from datetime import datetime
import pandas as pd

# Cấu hình trang web Streamlit (Sử dụng giao diện rộng rãi)
st.set_page_config(page_title="Hệ thống giám sát VPD", page_icon="🌿", layout="centered")

# --- TIÊU ĐỀ CHÍNH ---
st.markdown("<h2 style='text-align: center; color: #2E7D32;'>🌿 HỆ THỐNG GIÁM SÁT & TÍNH TOÁN VPD</h2>", unsafe_allow_html=True)
st.write("")

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

# --- CONTAINER 1: KHU VỰC ĐIỀU KHIỂN & ĐỒNG HỒ ---
with st.container(border=True):
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("""▶️ Bắt đầu chạy tự động""", type="primary", use_container_width=True, disabled=st.session_state.is_running):
            st.session_state.is_running = True
            st.rerun()
    with col_btn2:
        if st.button("""⏸️ Tạm dừng hệ thống""", type="secondary", use_container_width=True, disabled=not st.session_state.is_running):
            st.session_state.is_running = False
            st.rerun()

# Cấu hình chu kỳ quét ngầm
run_interval = 1 if st.session_state.is_running else 999999

@st.fragment(run_every=run_interval)
def vpd_controlled_monitor():
    if st.session_state.is_running:
        st.session_state.countdown -= 1
        if st.session_state.countdown < 0:
            trigger_new_data()
            
    # Hiển thị thanh tiến trình đếm ngược lồng vào trong khung điều khiển
    if st.session_state.is_running:
        st.write(f"⏳ Tự động đổi số sau: **{st.session_state.countdown}** giây")
        st.progress(st.session_state.countdown / 30)
    else:
        st.info("💡 Hệ thống đang tạm dừng. Bấm nút màu xanh phía trên để bắt đầu chạy tự động.")

    # --- CONTAINER 2: THÔNG SỐ HIỆN TẠI ---
    st.write("")
    with st.container(border=True):
        st.markdown("<p style='color: gray; font-size: 14px; margin-bottom: 5px;'>📊 THÔNG SỐ THỜI GIAN THỰC</p>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="🌡️ Nhiệt độ", value=f"{st.session_state.temp} °C")
        with col2:
            st.metric(label="💧 Độ ẩm", value=f"{st.session_state.rh} %")
        st.caption(f"⏱️ Cập nhật lúc: {st.session_state.last_updated} (Lần đo thứ: {st.session_state.stt_counter})")

    # --- CONTAINER 3: KẾT QUẢ VPD & ĐÁNH GIÁ ---
    vpd_result = calculate_vpd(st.session_state.temp, st.session_state.rh)
    
    st.write("")
    with st.container(border=True):
        st.markdown("<p style='color: gray; font-size: 14px; margin-bottom: 5px;'>🎯 CHỈ SỐ VPD ĐẦU RA</p>", unsafe_allow_html=True)
        st.metric(label="Áp suất hơi thâm hụt (Vapor Pressure Deficit)", value=f"{vpd_result:.2f} kPa")
        
        # Đánh giá môi trường tương ứng
        if vpd_result < 0.4:
            st.warning("""⚠️ **VPD quá thấp (Quá ẩm):** Cây khó thoát nước, dễ bị nấm bệnh.""")
        elif 0.4 <= vpd_result <= 0.8:
            st.info("""🌱 **VPD Thấp:** Phù hợp cho giai đoạn nhân giống, kích rễ, cây con.""")
        elif 0.8 < vpd_result <= 1.2:
            st.success("""✅ **VPD Lý tưởng:** Môi trường hoàn hảo cho đa số các loại cây trồng lớn mạnh.""")
        elif 1.2 < vpd_result <= 1.6:
            st.info("""🍂 **VPD Hơi cao:** Phù hợp cho giai đoạn cây ra hoa hoặc kết trái.""")
        else:
            st.error("""🚨 **VPD quá cao (Quá khô):** Cây mất nước nhanh, dễ bị héo và đóng khí khổng.""")

    # --- CONTAINER 4: LỊCH SỬ DỮ LIỆU ---
    st.write("")
    with st.container(border=True):
        st.markdown("<p style='color: gray; font-size: 14px; margin-bottom: 10px;'>📋 LỊCH SỬ DỮ LIỆU ĐÃ GHI NHẬN</p>", unsafe_allow_html=True)
        
        df_history = pd.DataFrame(st.session_state.history)
        st.dataframe(df_history, use_container_width=True, hide_index=True)
        
        # Nút xóa lịch sử nhỏ gọn đặt sát góc
        col_space, col_del = st.columns([4, 1])
        with col_del:
            if st.button("""🗑️ Xóa lịch sử""", type="secondary", use_container_width=True):
                st.session_state.stt_counter = 1
                st.session_state.history = [{
                    "STT": st.session_state.stt_counter,
                    "Thời gian": st.session_state.last_updated,
                    "Nhiệt độ (°C)": st.session_state.temp,
                    "Độ ẩm (%)": st.session_state.rh,
                    "VPD (kPa)": round(vpd_result, 2)
                }]
                st.rerun()

# Chạy toàn bộ chương trình Dashboard
vpd_controlled_monitor()
