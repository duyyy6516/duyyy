import streamlit as st
import random
import math
from datetime import datetime
import pandas as pd
import altair as alt  # Thêm thư viện Altair để tối ưu biểu đồ nâng cao

# Cấu hình trang web Streamlit
st.set_page_config(page_title="Hệ thống giám sát VPD Đà Lạt", page_icon="🌿", layout="centered")

# --- TIÊU ĐỀ CHÍNH ---
st.markdown("<h2 style='text-align: center; color: #2E7D32;'>🌿 HỆ THỐNG GIÁM SÁT & TÍNH TOÁN VPD ĐÀ LẠT</h2>", unsafe_allow_html=True)
st.write("")

# --- CÔNG THỨC TÍNH VPD ---
def calculate_vpd(temp, rh):
    if temp == 0 and rh == 0:
        return 0.0
    vp_sat = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    vpd = vp_sat * (1.0 - (rh / 100.0))
    return vpd

# --- HÀM RANDOM THÔNG MINH ---
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
if 'temp' not in st.session_state:
    st.session_state.temp = 0.0
if 'rh' not in st.session_state:
    st.session_state.rh = 0.0
if 'countdown' not in st.session_state:
    st.session_state.countdown = 30  
if 'last_updated' not in st.session_state:
    st.session_state.last_updated = "--:--:--"
if 'stt_counter' not in st.session_state:
    st.session_state.stt_counter = 0 
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
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

# --- CONTAINER 1: CẤU HÌNH THEO CÂY TRỒNG ĐÀ LẠT ---
with st.container(border=True):
    st.markdown("<p style='color: #2E7D32; font-size: 15px; font-weight: bold; margin-bottom: 2px;'>⚙️ CẤU HÌNH NGƯỠNG VPD THEO CÂY TRỒNG ĐÀ LẠT</p>", unsafe_allow_html=True)
    
    plant_option = st.selectbox(
        "Chọn loại cây trồng đang canh tác:",
        ["🍓 Dâu tây Đà Lạt", "🌹 Hoa hồng nhà kính", "🌼 Hoa cúc / Hoa đồng tiền", "🍅 Cà chua bi / 🫑 Ớt chuông", "🛠️ Tùy chỉnh thủ công"],
        disabled=st.session_state.is_running
    )
    
    if plant_option == "🍓 Dâu tây Đà Lạt":
        default_range = (0.6, 1.0)
    elif plant_option == "🌹 Hoa hồng nhà kính":
        default_range = (0.8, 1.2)
    elif plant_option == "🌼 Hoa cúc / Hoa đồng tiền":
        default_range = (0.7, 1.1)
    elif plant_option == "🍅 Cà chua bi / 🫑 Ớt chuông":
        default_range = (0.8, 1.4)
    else:
        default_range = (0.8, 1.2)

    vpd_range = st.slider(
        "Khoảng VPD tối ưu (kPa):",
        min_value=0.0,
        max_value=3.0,
        value=default_range,
        step=0.1,
        disabled=st.session_state.is_running or (plant_option != "🛠️ Tùy chỉnh thủ công")
    )
    vpd_min, vpd_max = vpd_range
    
    if st.session_state.is_running:
        st.caption("🔒 *Đã khóa cấu hình vì hệ thống đang chạy. Bấm Tạm dừng để chỉnh sửa.*")
    elif plant_option != "🛠️ Tùy chỉnh thủ công":
        st.caption(f"ℹ️ *Đang áp dụng ngưỡng tự động của **{plant_option}**: {vpd_min} - {vpd_max} kPa.*")
    else:
        st.caption(f"🔓 Chế độ thủ công: {vpd_min} - {vpd_max} kPa.")

st.write("")

# --- CONTAINER 2: KHU VỰC ĐIỀU KHIỂN & ĐỒNG HỒ ---
with st.container(border=True):
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("""▶️ Bắt đầu chạy tự động""", type="primary", use_container_width=True, disabled=st.session_state.is_running):
            st.session_state.is_running = True
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
            
    if st.session_state.is_running:
        st.write(f"⏳ Tự động đổi số sau: **{st.session_state.countdown}** giây")
        st.progress(st.session_state.countdown / 30)
    else:
        st.info("💡 Hệ thống đang tạm dừng. Bạn có thể thay đổi loại cây trồng hoặc ngưỡng cấu hình phía trên.")

    # --- CONTAINER 3: THÔNG SỐ HIỆN TẠI ---
    st.write("")
    with st.container(border=True):
        st.markdown("<p style='color: gray; font-size: 14px; margin-bottom: 5px;'>📊 THÔNG SỐ THỜI GIAN THỰC</p>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="🌡️ Nhiệt độ", value=f"{st.session_state.temp} °C" if st.session_state.stt_counter > 0 else "-- °C")
        with col2:
            st.metric(label="💧 Độ ẩm", value=f"{st.session_state.rh} %" if st.session_state.stt_counter > 0 else "-- %")
        st.caption(f"⏱️ Cập nhật lúc: {st.session_state.last_updated} (Lần đo thứ: {st.session_state.stt_counter})")

    # --- CONTAINER 4: KẾT QUẢ VPD, ĐÁNH GIÁ & GIẢI PHÁP ---
    vpd_result = calculate_vpd(st.session_state.temp, st.session_state.rh)
    
    st.write("")
    with st.container(border=True):
        st.markdown("<p style='color: gray; font-size: 14px; margin-bottom: 5px;'>🎯 CHỈ SỐ VPD ĐẦU RA</p>", unsafe_allow_html=True)
        st.metric(label="Áp suất hơi thâm hụt (Vapor Pressure Deficit)", value=f"{vpd_result:.2f} kPa" if st.session_state.stt_counter > 0 else "-- kPa")
        
        if st.session_state.stt_counter > 0:
            st.markdown(f"**🔍 Đánh giá trạng thái phù hợp cho [{plant_option}]:**")
            if vpd_result < vpd_min:
                st.warning(f"⚠️ **VPD đang thấp hơn ngưỡng tối ưu ({vpd_result:.2f} < {vpd_min} kPa):** Môi trường đang quá ẩm.")
                st.info("💡 **Giải pháp:** Bật quạt thông gió, kích hoạt máy hút ẩm hoặc tăng nhiệt độ phòng nuôi.")
            elif vpd_min <= vpd_result <= vpd_max:
                st.success(f"✅ **VPD nằm trong khoảng lý tưởng ({vpd_min} ≤ {vpd_result:.2f} ≤ {vpd_max} kPa):** Môi trường hoàn hảo!")
                st.info("💡 **Giải pháp:** Duy trì hệ thống ổn định ở trạng thái hiện tại.")
            else:
                st.error(f"🚨 **VPD đang cao hơn ngưỡng tối ưu ({vpd_result:.2f} > {vpd_max} kPa):** Môi trường đang quá khô.")
                st.info("💡 **Giải pháp:** Bật ngay hệ thống phun sương mịn, kéo rèm che nắng và tăng tưới nước gốc.")
        else:
            st.write("Chờ hệ thống kích hoạt...")

    # --- CONTAINER NEW: BIỂU ĐỒ XU HƯỚNG THỜI GIAN THỰC TỰ ĐỘNG CÂN ĐỐI ---
    if len(st.session_state.history) > 0:
        st.write("")
        with st.container(border=True):
            st.markdown("<p style='color: gray; font-size: 14px; margin-bottom: 10px;'>📈 BIỂU ĐỒ XU HƯỚNG TỰ ĐỘNG TỐI ƯU GIAO DIỆN</p>", unsafe_allow_html=True)
            
            # Sắp xếp lịch sử từ cũ đến mới để vẽ
            df_chart = pd.DataFrame(st.session_state.history).iloc[::-1]
            
            tab_temp, tab_rh, tab_vpd = st.tabs(["🌡️ Biểu đồ Nhiệt độ", "💧 Biểu đồ Độ ẩm", "🎯 Biểu đồ chỉ số VPD"])
            
            with tab_temp:
                # THAY ĐỔI QUAN TRỌNG: Đổi thành 'STT:O' (Ordinal) để ép trục hoành chỉ hiện số nguyên rời rạc
                chart_temp = alt.Chart(df_chart).mark_line(color="#FF4B4B", point=True).encode(
                    x=alt.X('STT:O', axis=alt.Axis(title="Lần đo (STT)", labelAngle=0)),
                    y=alt.Y('Nhiệt độ (°C):Q', scale=alt.Scale(zero=False)),
                    tooltip=['STT', 'Thời gian', 'Nhiệt độ (°C)']
                ).properties(height=300)
                st.altair_chart(chart_temp, use_container_width=True)
                
            with tab_rh:
                # Thay 'STT:O' cho biểu đồ độ ẩm
                chart_rh = alt.Chart(df_chart).mark_line(color="#0068C9", point=True).encode(
                    x=alt.X('STT:O', axis=alt.Axis(title="Lần đo (STT)", labelAngle=0)),
                    y=alt.Y('Độ ẩm (%):Q', scale=alt.Scale(zero=False)),
                    tooltip=['STT', 'Thời gian', 'Độ ẩm (%)']
                ).properties(height=300)
                st.altair_chart(chart_rh, use_container_width=True)
                
            with tab_vpd:
                # Thay 'STT:O' cho biểu đồ VPD
                chart_vpd = alt.Chart(df_chart).mark_line(color="#2E7D32", point=True).encode(
                    x=alt.X('STT:O', axis=alt.Axis(title="Lần đo (STT)", labelAngle=0)),
                    y=alt.Y('VPD (kPa):Q', scale=alt.Scale(zero=False)),
                    tooltip=['STT', 'Thời gian', 'VPD (kPa)']
                ).properties(height=300)
                st.altair_chart(chart_vpd, use_container_width=True)

    # --- CONTAINER 5: LỊCH SỬ DỮ LIỆU BẢNG ---
    st.write("")
    with st.container(border=True):
        st.markdown("<p style='color: gray; font-size: 14px; margin-bottom: 10px;'>📋 LỊCH SỬ DỮ LIỆU ĐÃ GHI NHẬN</p>", unsafe_allow_html=True)
        
        if len(st.session_state.history) > 0:
            df_history = pd.DataFrame(st.session_state.history)
            st.dataframe(df_history, use_container_width=True, hide_index=True)
        else:
            st.write("Chưa có dữ liệu lịch sử.")
        
        # Nút xóa lịch sử
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
