import streamlit as st
import random
import math
from datetime import datetime
import pandas as pd

# Cấu hình trang web Streamlit
st.set_page_config(page_title="Hệ thống giám sát VPD", page_icon="🌿", layout="centered")

# --- TIÊU ĐỀ CHÍNH ---
st.markdown("<h2 style='text-align: center; color: #2E7D32;'>🌿 HỆ THỐNG GIÁM SÁT & TÍNH TOÁN VPD</h2>", unsafe_allow_html=True)
st.write("")

# --- CÔNG THỨC TÍNH VPD ---
def calculate_vpd(temp, rh):
    if temp == 0 and rh == 0:
        return 0.0
    vp_sat = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    vpd = vp_sat * (1.0 - (rh / 100.0))
    return vpd

# --- HÀM RANDOM THÔNG MINH (ƯU TIÊN KỊCH BẢN TỐT) ---
def get_smart_random_data():
    rate = random.randint(1, 100)
    if rate <= 70:
        temp = round(random.uniform(22.0, 28.5), 1)
        rh = round(random.uniform(60.0, 78.0), 1)
    elif rate <= 85:
        temp = round(random.uniform(29.0, 33.0), 1)
        rh = round(random.uniform(45.0, 55.0), 1)
    else:
        if random.choice([True, False]):
            temp = round(random.uniform(34.0, 38.0), 1)
            rh = round(random.uniform(30.0, 40.0), 1)
        else:
            temp = round(random.uniform(16.0, 21.0), 1)
            rh = round(random.uniform(85.0, 95.0), 1)
    return temp, rh

# --- KHỞI TẠO BIẾN TRONG SESSION STATE ---
# Mới mở web: Đặt tất cả thông số bằng 0
if 'temp' not in st.session_state:
    st.session_state.temp = 0.0
if 'rh' not in st.session_state:
    st.session_state.rh = 0.0
if 'countdown' not in st.session_state:
    st.session_state.countdown = 30  
if 'last_updated' not in st.session_state:
    st.session_state.last_updated = "--:--:--"
if 'stt_counter' not in st.session_state:
    st.session_state.stt_counter = 0 # Bắt đầu từ 0 (chưa có lần đo nào)
if 'is_running' not in st.session_state:
    st.session_state.is_running = False

# Mới mở web: Lịch sử hoàn toàn trống rỗng
if 'history' not in st.session_state:
    st.session_state.history = []

# --- HÀM CẬP NHẬT DỮ LIỆU MỚI ---
def trigger_new_data():
    st.session_state.temp, st.session_state.rh = get_smart_random_data()
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
            # Nếu là lần đầu tiên bấm nút, kích hoạt lấy dữ liệu phát đầu tiên luôn
            if st.session_state.stt_counter == 0:
                trigger_new_data()
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
            
    # Hiển thị thanh tiến trình đếm ngược
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
            st.metric(label="🌡️ Nhiệt độ", value=f"{st.session_state.temp} °C" if st.session_state.stt_counter > 0 else "-- °C")
        with col2:
            st.metric(label="💧 Độ ẩm", value=f"{st.session_state.rh} %" if st.session_state.stt_counter > 0 else "-- %")
        st.caption(f"⏱️ Cập nhật lúc: {st.session_state.last_updated} (Lần đo thứ: {st.session_state.stt_counter})")

    # --- CONTAINER 3: KẾT QUẢ VPD & ĐÁNH GIÁ ---
    vpd_result = calculate_vpd(st.session_state.temp, st.session_state.rh)
    
    st.write("")
    with st.container(border=True):
        st.markdown("<p style='color: gray; font-size: 14px; margin-bottom: 5px;'>🎯 CHỈ SỐ VPD ĐẦU RA</p>", unsafe_allow_html=True)
        st.metric(label="Áp suất hơi thâm hụt (Vapor Pressure Deficit)", value=f"{vpd_result:.2f} kPa" if st.session_state.stt_counter > 0 else "-- kPa")
        
        # Đánh giá môi trường tương ứng (Chỉ đánh giá khi đã bấm chạy)
        if st.session_state.stt_counter > 0:
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
        else:
            st.write("Chờ hệ thống kích hoạt...")

    # --- CONTAINER 4: LỊCH SỬ DỮ LIỆU ---
    st.write("")
    with st.container(border=True):
        st.markdown("<p style='color: gray; font-size: 14px; margin-bottom: 10px;'>📋 LỊCH SỬ DỮ LIỆU ĐÃ GHI NHẬN</p>", unsafe_allow_html=True)
        
        if len(st.session_state.history) > 0:
            df_history = pd.DataFrame(st.session_state.history)
            st.dataframe(df_history, use_container_width=True, hide_index=True)
        else:
            st.write("Chưa có dữ liệu lịch sử.")
        
        # Nút xóa lịch sử nhỏ gọn đặt sát góc
        col_space, col_del = st.columns([4, 1])
        with col_del:
            if st.button("""🗑️ Xóa lịch sử""", type="secondary", use_container_width=True, disabled=len(st.session_state.history) == 0):
                st.session_state.stt_counter = 0
                st.session_state.temp = 0.0
                st.session_state.rh = 0.0
                st.session_state.last_updated = "--:--:--"
                st.session_state.history = []
                st.rerun()

# Chạy toàn bộ chương trình Dashboard
vpd_controlled_monitor()
