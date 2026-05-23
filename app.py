import streamlit as st
import random
import math
from datetime import datetime
import pandas as pd

# Cấu hình trang web Streamlit
st.set_page_config(page_title="Giám sát VPD & Lịch sử STT", page_icon="🌿", layout="centered")

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
    st.session_state.countdown = 30  
if 'last_updated' not in st.session_state:
    st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")

# Khởi tạo biến đếm số thứ tự (STT), bắt đầu từ 1
if 'stt_counter' not in st.session_state:
    st.session_state.stt_counter = 1

# Khởi tạo danh sách lưu lịch sử
if 'history' not in st.session_state:
    first_vpd = calculate_vpd(st.session_state.temp, st.session_state.rh)
    st.session_state.history = [{
        "STT": st.session_state.stt_counter, # Lần đầu tiên mang STT = 1
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
    
    # Tăng số thứ tự lên 1 cho lần đo tiếp theo
    st.session_state.stt_counter += 1
    
    new_vpd = calculate_vpd(st.session_state.temp, st.session_state.rh)
    
    new_record = {
        "STT": st.session_state.stt_counter, # Gán STT mới tăng
        "Thời gian": st.session_state.last_updated,
        "Nhiệt độ (°C)": st.session_state.temp,
        "Độ ẩm (%)": st.session_state.rh,
        "VPD (kPa)": round(new_vpd, 2)
    }
    # Đẩy lên đầu bảng
    st.session_state.history.insert(0, new_record)

# --- ĐOẠN CODE CHẠY LẠI MỖI 1 GIÂY ---
@st.fragment(run_every=1)
def vpd_monitor_with_history_stt():
    # 1. Trừ thời gian đếm ngược
    st.session_state.countdown -= 1
    
    # 2. Hết 30s kích hoạt số mới
    if st.session_state.countdown < 0:
        trigger_new_data()
    
    # 3. HIỂN THỊ SỐ ĐẾM NGƯỢC
    st.write(f"### ⏳ Tự động đổi số sau: **{st.session_state.countdown}** giây")
    st.progress(st.session_state.countdown / 30)
    
    st.caption(f"🔄 Cập nhật dữ liệu mới nhất lúc: {st.session_state.last_updated} (Lần đo thứ: {st.session_state.stt_counter})")
    st.write("---")

    # 4. HIỂN THỊ THÔNG SỐ HIỆN TẠI
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="🌡️ Nhiệt độ hiện tại", value=f"{st.session_state.temp} °C")
    with col2:
        st.metric(label="💧 Độ ẩm hiện tại", value=f"{st.session_state.rh} %")
        
    vpd_result = calculate_vpd(st.session_state.temp, st.session_state.rh)
    
    st.write("---")
    st.subheader("Chỉ số VPD hiện tại:")
    st.metric(label="Áp suất hơi thâm hụt (Vapor Pressure Deficit)", value=f"{vpd_result:.2f} kPa")
    
    # Đánh giá môi trường
    if vpd_result < 0.4:
        st.warning("⚠️ **VPD quá thấp (Môi trường quá ẩm):** Cây khó thoát nước, dễ bị nấm bệnh.")
    elif 0.4 <= vpd_result <= 0.8:
        st.info("🌱 **VPD Thấp:** Phù hợp cho giai đoạn nhân giống, kích rễ hoặc cây con.")
    elif 0.8 < vpd_result <= 1.2:
        st.success("✅ **VPD Lý tưởng:** Môi trường hoàn hảo cho hầu hết các loại cây.")
    elif 1.2 < vpd_result <= 1.6:
        st.info("🍂 **VPD Hơi cao:** Phù hợp cho giai đoạn cây ra hoa hoặc tạo quả.")
    else:
        st.error("🚨 **VPD quá cao (Môi trường quá khô):** Cây mất nước quá nhanh.")

    # Nút bấm đổi số khẩn cấp
    if st.button("🎲 Random Ngay Lập Tức", type="secondary"):
        trigger_new_data()
        st.rerun()

    # --- 5. HIỂN THỊ LỊCH SỬ DỮ LIỆU CÓ STT ---
    st.write("---")
    st.subheader("📋 Lịch Sử Dữ Liệu Đã Ghi Nhận")
    
    df_history = pd.DataFrame(st.session_state.history)
    
    # Hiển thị bảng dữ liệu ra màn hình
    st.dataframe(df_history, use_container_width=True, hide_index=True)
    
    # Nút bấm xóa lịch sử (reset về 1)
    if st.button("🗑️ Xóa Lịch Sử"):
        st.session_state.stt_counter = 1
        st.session_state.history = [{
            "STT": st.session_state.stt_counter,
            "Thời gian": st.session_state.last_updated,
            "Nhiệt độ (°C)": st.session_state.temp,
            "Độ ẩm (%)": st.session_state.rh,
            "VPD (kPa)": round(vpd_result, 2)
        }]
        st.rerun()

# Chạy toàn bộ hệ thống
vpd_monitor_with_history_stt()
