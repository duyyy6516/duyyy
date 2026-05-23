import streamlit as st
import random
import math
from datetime import datetime

# Cấu hình trang web Streamlit
st.set_page_config(page_title="Tính toán VPD Tự Động", page_icon="🌿", layout="centered")

st.title("Hệ Thống Giám Sát & Tính Toán VPD Tự Động 🌿")
st.write("Hệ thống sẽ **tự động cập nhật thông số mới sau mỗi 30 giây**.")

# --- CÔNG THỨC TÍNH VPD ---
def calculate_vpd(temp, rh):
    """
    VP_sat = 0.61078 * e^((17.27 * T) / (T + 237.3))
    VPD = VP_sat * (1 - RH/100)
    """
    vp_sat = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    vpd = vp_sat * (1.0 - (rh / 100.0))
    return vpd

# --- ĐOẠN CODE TỰ ĐỘNG CHẠY LẠI MỖI 30 GIÂY ---
# Thêm decorator @st.fragment với tham số run_every=30 (đơn vị là giây)
@st.fragment(run_every=30)
def vpd_monitor_fragment():
    # 1. Random thông số mới mỗi khi fragment này được kích hoạt
    temp = round(random.uniform(15.0, 38.0), 1)
    rh = round(random.uniform(30.0, 95.0), 1)
    
    # 2. Tính toán VPD
    vpd_result = calculate_vpd(temp, rh)
    
    # 3. Hiển thị thời gian cập nhật gần nhất để bạn dễ theo dõi
    now = datetime.now().strftime("%H:%M:%S")
    st.caption(f"🔄 Cập nhật lần cuối lúc: **{now}** (Sẽ tự động đổi sau 30 giây...)")
    
    # 4. Hiển thị Nhiệt độ & Độ ẩm
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="🌡️ Nhiệt độ", value=f"{temp} °C")
    with col2:
        st.metric(label="💧 Độ ẩm", value=f"{rh} %")
        
    st.write("---")
    st.subheader("Chỉ số VPD hiện tại:")
    st.metric(label="Áp suất hơi thâm hụt (Vapor Pressure Deficit)", value=f"{vpd_result:.2f} kPa")
    
    # 5. Đánh giá môi trường
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

    # Thêm một nút bấm thủ công nếu người dùng muốn đổi số ngay lập tức mà không đợi 30s
    if st.button("🎲 Random Ngay Lập Tức"):
        st.rerun()

# Gọi hàm fragment để chạy trên giao diện
vpd_monitor_fragment()
