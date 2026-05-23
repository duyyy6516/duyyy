import streamlit as st
import random
import math
from datetime import datetime

# Cấu hình trang web Streamlit
st.set_page_config(page_title="Tính toán VPD có Đếm Ngược", page_icon="🌿", layout="centered")

st.title("Hệ Thống Giám Sát & Tính Toán VPD Tự Động 🌿")

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
    st.session_state.countdown = 30  # Bắt đầu đếm từ 30 giây
if 'last_updated' not in st.session_state:
    st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")

# --- ĐOẠN CODE CHẠY LẠI MỖI 1 GIÂY ĐỂ GIẢM SỐ ĐẾM NGƯỢC ---
@st.fragment(run_every=1)
def vpd_monitor_with_countdown():
    # Mỗi 1 giây trừ đi 1
    st.session_state.countdown -= 1
    
    # Nếu đếm ngược về hết số (dưới 0) thì random số mới và reset về 30
    if st.session_state.countdown < 0:
        st.session_state.temp = round(random.uniform(15.0, 38.0), 1)
        st.session_state.rh = round(random.uniform(30.0, 95.0), 1)
        st.session_state.countdown = 30 
        st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")
    
    # HIỂN THỊ SỐ ĐẾM NGƯỢC CHẠY LIÊN TỤC Ở ĐÂY
    st.write(f"### ⏳ Tự động đổi số sau: **{st.session_state.countdown}** giây")
    st.progress(st.session_state.countdown / 30) # Thanh tiến trình chạy lùi theo
    
    st.caption(f"🔄 Cập nhật dữ liệu mới nhất lúc: {st.session_state.last_updated}")
    st.write("---")

    # HIỂN THỊ THÔNG SỐ
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="🌡️ Nhiệt độ", value=f"{st.session_state.temp} °C")
    with col2:
        st.metric(label="💧 Độ ẩm", value=f"{st.session_state.rh} %")
        
    # TÍNH TOÁN VPD
    vpd_result = calculate_vpd(st.session_state.temp, st.session_state.rh)
    
    st.write("---")
    st.subheader("Chỉ số VPD hiện tại:")
    st.metric(label="Áp suất hơi thâm hụt (Vapor Pressure Deficit)", value=f"{vpd_result:.2f} kPa")
    
    # ĐÁNH GIÁ MÔI TRƯỜNG
    st.write("**Đánh giá môi trường:**")
    if vpd_result < 0.4:
        st.warning("⚠️ **VPD quá thấp (Môi trường quá ẩm):** Cây khó thoát nước, dễ bị nấm bệnh tấn công.")
    elif 0.4 <= vpd_result <= 0.8:
        st.info("🌱 **VPD Thấp:** Phù hợp cho giai đoạn nhân giống, kích rễ hoặc cây con.")
    elif 0.8 < vpd_result <= 1.2:
        st.success("✅ **VPD Lý tưởng:** Môi trường hoàn hảo cho hầu hết các loại cây phát triển mạnh mẽ.")
    elif 1.2 < vpd_result <= 1.6:
        st.info("🍂 **VPD Hơi cao:** Phù hợp cho giai đoạn cây ra hoa hoặc tạo quả.")
    else:
        st.error("🚨 **VPD quá cao (Môi trường quá khô):** Cây mất nước quá nhanh, buộc phải đóng lỗ khí khổng, ngừng lớn.")

# Chạy hàm
vpd_monitor_with_countdown()
