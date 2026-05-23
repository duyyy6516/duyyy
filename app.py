import streamlit as st
import random
import math

# Cấu hình trang web Streamlit
st.set_page_config(page_title="Tính toán VPD", page_icon="🌿", layout="centered")

st.title("Hệ Thống Giám Sát & Tính Toán VPD 🌿")
st.write("Nhấn nút bên dưới để lấy ngẫu nhiên thông số nhiệt độ, độ ẩm và tính toán chỉ số VPD tự động.")

# --- CÔNG THỨC TÍNH VPD ---
def calculate_vpd(temp, rh):
    """
    Công thức tính VPD (kPa):
    VP_sat = 0.61078 * e^((17.27 * T) / (T + 237.3))
    VPD = VP_sat * (1 - RH/100)
    """
    # 1. Tính Áp suất hơi bão hòa (VP_sat) ở nhiệt độ hiện tại
    vp_sat = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    
    # 2. Tính VPD dựa trên độ ẩm tương đối (RH)
    vpd = vp_sat * (1.0 - (rh / 100.0))
    return vpd

# --- QUẢN LÝ TRẠNG THÁI (Session State) ---
# Dùng session_state để lưu lại giá trị cũ, không bị reset khi trang load lại
if 'temp' not in st.session_state:
    st.session_state.temp = 25.0  # Giá trị mặc định ban đầu
if 'rh' not in st.session_state:
    st.session_state.rh = 60.0    # Giá trị mặc định ban đầu

# --- NÚT BẤM RANDOM ---
if st.button("🎲 Random Thông Số Mới", type="primary"):
    # Giới hạn random Nhiệt độ từ 15°C đến 38°C, Độ ẩm từ 30% đến 95%
    st.session_state.temp = round(random.uniform(15.0, 38.0), 1)
    st.session_state.rh = round(random.uniform(30.0, 95.0), 1)

# --- HIỂN THỊ THÔNG SỐ NHIỆT ĐỘ & ĐỘ ẨM ---
st.write("---")
col1, col2 = st.columns(2)

with col1:
    st.metric(label="🌡️ Nhiệt độ", value=f"{st.session_state.temp} °C")

with col2:
    st.metric(label="💧 Độ ẩm", value=f"{st.session_state.rh} %")

# --- TÍNH TOÁN VÀ HIỂN THỊ KẾT QUẢ VPD ---
vpd_result = calculate_vpd(st.session_state.temp, st.session_state.rh)

st.write("---")
st.subheader("Chỉ số VPD hiện tại:")
# Hiển thị số VPD lớn, làm tròn 2 chữ số thập phân
st.metric(label="Áp suất hơi thâm hụt (Vapor Pressure Deficit)", value=f"{vpd_result:.2f} kPa")

# --- ĐÁNH GIÁ MÔI TRƯỜNG DỰA TRÊN VPD (Dành cho cây trồng nói chung) ---
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
