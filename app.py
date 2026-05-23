import streamlit as st
import random
import math
from datetime import datetime, timedelta
import pandas as pd
import altair as alt

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

# --- HÀM RANDOM THEO CHU KỲ THỜI GIAN THỰC TẾ TRONG NGÀY ---
def get_weather_by_time(sim_time):
    hour = sim_time.hour
    if 7 <= hour < 11: # Sáng
        temp = round(random.uniform(20.0, 25.5), 1)
        rh = round(random.uniform(65.0, 80.0), 1)
    elif 11 <= hour < 15: # Trưa
        temp = round(random.uniform(26.0, 31.0), 1)
        rh = round(random.uniform(40.0, 55.0), 1)
    elif 15 <= hour < 19: # Chiều
        temp = round(random.uniform(19.0, 25.0), 1)
        rh = round(random.uniform(60.0, 75.0), 1)
    else: # Tối & Đêm (Đến 24h)
        temp = round(random.uniform(14.0, 18.5), 1)
        rh = round(random.uniform(80.0, 95.0), 1)
    return temp, rh

# --- HÀM TỰ ĐỘNG PHÂN TÍCH THEO BUỔI & ĐƯA RA HƯỚNG XỬ LÝ CHI TIẾT ---
def analyze_day_by_blocks(history_list, vpd_min, vpd_max, target_date_str):
    day_data = [r for r in history_list if r["Ngày"] == target_date_str]
    if not day_data:
        return None
        
    blocks = {
        "🌅 Sáng (07h-11h)": [],
        "☀️ Trưa (11h-15h)": [],
        "🌤️ Chiều (15h-19h)": [],
        "🌙 Tối (19h-24h)": []
    }
    
    for r in day_data:
        time_obj = datetime.strptime(r["Hiển thị Giờ"], "%H:%M")
        hour = time_obj.hour
        vpd_val = r["VPD (kPa)"]
        
        if 7 <= hour < 11:
            blocks["🌅 Sáng (07h-11h)"].append(vpd_val)
        elif 11 <= hour < 15:
            blocks["☀️ Trưa (11h-15h)"].append(vpd_val)
        elif 15 <= hour < 19:
            blocks["🌤️ Chiều (15h-19h)"].append(vpd_val)
        else:
            blocks["🌙 Tối (19h-24h)"].append(vpd_val)
            
    summary = []
    for block_name, vpd_list in blocks.items():
        if vpd_list:
            avg_vpd = sum(vpd_list) / len(vpd_list)
            
            if avg_vpd < vpd_min:
                danh_gia = "🟦 Quá ẩm"
                if "Sáng" in block_name:
                    huong_xu_ly = "Mở bạt hông muộn hoặc bật quạt gió để xua tan sương ẩm ban đêm đọng trên lá."
                elif "Trưa" in block_name or "Chiều" in block_name:
                    huong_xu_ly = "Trời âm u/mưa khép kín. Bật quạt đối lưu mạnh, hạn chế tưới nước dầm gốc."
                else:
                    huong_xu_ly = "Ẩm độ ban đêm rất cao. Tuyệt đối không tưới muộn sau 16h; bật quạt thông gió định kỳ."
            elif vpd_min <= avg_vpd <= vpd_max:
                danh_gia = "🟩 Lý tưởng"
                huong_xu_ly = "Môi trường hoàn hảo. Duy trì chế độ thông thoáng tự nhiên và lịch tưới hiện tại."
            else:
                danh_gia = "🟥 Quá khô"
                if "Sáng" in block_name:
                    huong_xu_ly = "Nắng lên nhanh làm tăng nhiệt. Cần kích hoạt nhẹ hệ thống tưới nhỏ giọt để cấp ẩm gốc."
                elif "Trưa" in block_name:
                    huong_xu_ly = "Cao điểm nắng nóng cực độ! Kéo lưới đen cắt nắng (giảm 30%), bật phun sương mịn 5-10 phút/lần."
                elif "Chiều" in block_name:
                    huong_xu_ly = "Nhiệt muộn vẫn cao. Bổ sung một lượt phun sương ngắn để hạ nhiệt trước khi đóng vách kính."
                else:
                    huong_xu_ly = "Hiện tượng bất thường (hiếm gặp ban đêm). Kiểm tra thiết bị sưởi hoặc đóng kín vách ngăn gió."
            
            summary.append({
                "Khoảng Thời Gian": block_name,
                "VPD TB (kPa)": round(avg_vpd, 2),
                "Đánh Giá": danh_gia,
                "Hướng Xử Lý Đề Xuất (Kỹ thuật nhà kính)": huong_xu_ly
            })
        else:
            summary.append({
                "Khoảng Thời Gian": block_name,
                "VPD TB (kPa)": "N/A",
                "Đánh Giá": "⚪ Thiếu số liệu",
                "Hướng Xử Lý Đề Xuất (Kỹ thuật nhà kính)": "Không có dữ liệu phân tích."
            })
    return pd.DataFrame(summary)

# --- HÀM DỰ BÁO XU HƯỚNG ---
def predict_vpd_trend_v2(history, vpd_min, vpd_max):
    if len(history) < 4:
        return "🔄 Hệ thống đang tích lũy dữ liệu nhà kính để phân tích...", "info"
    v0 = history[0]["VPD (kPa)"]
    v1 = history[1]["VPD (kPa)"]
    v2 = history[2]["VPD (kPa)"]
    v3 = history[3]["VPD (kPa)"]
    ma_hien_tai = (v0 + v1) / 2
    ma_truoc_do = (v2 + v3) / 2
    is_trending_up = ma_hien_tai > ma_truoc_do
    is_trending_down = ma_hien_tai < ma_truoc_do
    buffer = 0.15
    
    if vpd_min <= v0 <= vpd_max:
        if (v0 - vpd_min <= buffer) and is_trending_down:
            return f"🔮 DỰ BÁO SỚM: Chỉ số VPD ({v0:.2f} kPa) đang tiến sát biên dưới. Môi trường SẮP QUÁ ẨM!", "warning"
        elif (vpd_max - v0 <= buffer) and is_trending_up:
            return f"🔮 DỰ BÁO SỚM: Chỉ số VPD ({v0:.2f} kPa) đang tiến sát biên trên. Môi trường SẮP QUÁ KHÔ!", "error"
        else:
            hướng = "📈 xu hướng tăng" if is_trending_up else "📉 xu hướng giảm"
            return f"🟢 Ổn định: Chỉ số đi theo {hướng} nhưng vẫn nằm an toàn.", "success"
    else:
        if v0 < vpd_min:
            return f"🚨 BÁO ĐỘNG: Nhà kính đang bị QUÁ ẨM ({v0:.2f} < {vpd_min} kPa)!", "warning"
        else:
            return f"🚨 BÁO ĐỘNG: Nhà kính đang bị QUÁ KHÔ ({v0:.2f} > {vpd_max} kPa)!", "error"

# --- KHỞI TẠO BIẾN TRONG SESSION STATE ---
if 'temp' not in st.session_state: st.session_state.temp = 0.0
if 'rh' not in st.session_state: st.session_state.rh = 0.0
if 'countdown' not in st.session_state: st.session_state.countdown = 15 
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'history' not in st.session_state: st.session_state.history = []
if 'stt_counter' not in st.session_state: st.session_state.stt_counter = 0 
if 'daily_reports' not in st.session_state: st.session_state.daily_reports = {} 

# KHỞI TẠO THỜI GIAN MÔ PHỎNG
if 'simulated_time' not in st.session_state:
    st.session_state.simulated_time = "2026-05-24 07:00:00"

# --- HÀM CẬP NHẬT DỮ LIỆU MỚI ---
def trigger_new_data(vpd_min, vpd_max):
    current_sim_datetime = datetime.strptime(st.session_state.simulated_time, "%Y-%m-%d %H:%M:%S")
    current_date_str = current_sim_datetime.strftime("Ngày %d/%m")
    
    st.session_state.temp, st.session_state.rh = get_weather_by_time(current_sim_datetime)
    st.session_state.countdown = 15 
    st.session_state.stt_counter += 1
    new_vpd = calculate_vpd(st.session_state.temp, st.session_state.rh)
    
    status_text = "⚠️ Quá ẩm" if new_vpd < vpd_min else ("✅ Lý tưởng" if vpd_min <= new_vpd <= vpd_max else "🚨 Quá khô")
    
    new_record = {
        "STT": st.session_state.stt_counter,
        "Ngày": current_date_str,
        "Thời gian mô phỏng": current_sim_datetime, # Lưu đối tượng datetime nguyên bản cho biểu đồ (:T)
        "Hiển thị Giờ": current_sim_datetime.strftime("%H:%M"), # Dành cho bảng lịch sử dữ liệu dễ xem
        "Nhiệt độ (°C)": st.session_state.temp,
        "Độ ẩm (%)": st.session_state.rh,
        "VPD (kPa)": round(new_vpd, 2),
        "Trạng thái": status_text
    }
    st.session_state.history.insert(0, new_record)
    
    next_sim_datetime = current_sim_datetime + timedelta(minutes=30)
    
    if next_sim_datetime.hour == 0 and next_sim_datetime.minute == 0:
        report_df = analyze_day_by_blocks(st.session_state.history, vpd_min, vpd_max, current_date_str)
        if report_df is not None:
            st.session_state.daily_reports[current_date_str] = report_df
        next_sim_datetime = next_sim_datetime + timedelta(hours=7)
        
    st.session_state.simulated_time = next_sim_datetime.strftime("%Y-%m-%d %H:%M:%S")

# --- CONTAINER 1: CẤU HÌNH THEO CÂY TRỒNG ---
with st.container(border=True):
    st.markdown("<p style='color: #2E7D32; font-size: 15px; font-weight: bold; margin-bottom: 2px;'>⚙️ CẤU HÌNH NGƯỠNG VPD THEO CÂY TRỒNG ĐÀ LẠT</p>", unsafe_allow_html=True)
    plant_option = st.selectbox(
        "Chọn loại cây trồng đang canh tác:",
        ["🍓 Dâu tây Đà Lạt", "🌹 Hoa hồng nhà kính", "🌼 Hoa cúc / Hoa đồng tiền", "🍅 Cà chua bi / 🫑 Ớt chuông", "🛠️ Tùy chỉnh thủ công"],
        disabled=st.session_state.is_running
    )
    if plant_option == "🍓 Dâu tây Đà Lạt": default_range = (0.6, 1.0)
    elif plant_option == "🌹 Hoa hồng nhà kính": default_range = (0.8, 1.2)
    elif plant_option == "🌼 Hoa cúc / Hoa đồng tiền": default_range = (0.7, 1.1)
    elif plant_option == "🍅 Cà chua bi / 🫑 Ớt chuông": default_range = (0.8, 1.4)
    else: default_range = (0.8, 1.2)

    vpd_range = st.slider("Khoảng VPD tối ưu (kPa):", min_value=0.0, max_value=3.0, value=default_range, step=0.1, disabled=st.session_state.is_running or (plant_option != "🛠️ Tùy chỉnh thủ công"))
    vpd_min, vpd_max = vpd_range

st.write("")

# --- CONTAINER 2: KHU VỰC ĐIỀU KHIỂN & ĐỒNG HỒ ---
with st.container(border=True):
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("""▶️ Bắt đầu chạy tự động""", type="primary", use_container_width=True, disabled=st.session_state.is_running):
            st.session_state.is_running = True
            if st.session_state.stt_counter == 0: trigger_new_data(vpd_min, vpd_max)
            st.rerun()
    with col_btn2:
        if st.button("""⏸️ Tạm dừng hệ thống""", type="secondary", use_container_width=True, disabled=not st.session_state.is_running):
            st.session_state.is_running = False
            st.rerun()

run_interval = 1 if st.session_state.is_running else 999999

@st.fragment(run_every=run_interval)
def vpd_controlled_monitor():
    if st.session_state.is_running:
        st.session_state.countdown -= 1
        if st.session_state.countdown < 0: trigger_new_data(vpd_min, vpd_max)
            
    if st.session_state.is_running:
        st.write(f"⏳ Tự động đổi số sau: **{st.session_state.countdown}** giây")
        st.progress(st.session_state.countdown / 15)
    else:
        st.info("💡 Hệ thống đang tạm dừng.")

    current_sim_dt = datetime.strptime(st.session_state.simulated_time, "%Y-%m-%d %H:%M:%S")
    current_date_display = current_sim_dt.strftime("Ngày %d/%m")
    
    # --- CONTAINER 3: THÔNG SỐ HIỆN TẠI ---
    st.write("")
    with st.container(border=True):
        st.markdown(f"### ⏰ Thời gian nhà kính: <span style='color:#2E7D32;'>{current_date_display} - {current_sim_dt.strftime('%H:%M')}</span>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: st.metric(label="🌡️ Nhiệt độ", value=f"{st.session_state.temp} °C" if st.session_state.stt_counter > 0 else "-- °C")
        with col2: st.metric(label="💧 Độ ẩm", value=f"{st.session_state.rh} %" if st.session_state.stt_counter > 0 else "-- %")

    # --- CONTAINER 4: KẾT QUẢ VPD & BỘ NÃO DỰ BÁO ---
    vpd_result = calculate_vpd(st.session_state.temp, st.session_state.rh)
    st.write("")
    with st.container(border=True):
        st.metric(label="Áp suất hơi thâm hụt (VPD)", value=f"{vpd_result:.2f} kPa" if st.session_state.stt_counter > 0 else "-- kPa")
        if st.session_state.stt_counter > 0:
            trend_msg, msg_type = predict_vpd_trend_v2(st.session_state.history, vpd_min, vpd_max)
            if msg_type == "warning": st.warning(trend_msg)
            elif msg_type == "error": st.error(trend_msg)
            elif msg_type == "success": st.success(trend_msg)
            else: st.info(trend_msg)

    # --- CONTAINER 5: BÁO CÁO PHÂN TÍCH TỔNG KẾT THEO BUỔI KÈM HƯỚNG XỬ LÝ ---
    if st.session_state.daily_reports:
        st.write("")
        with st.container(border=True):
            st.markdown("<p style='color: #2E7D32; font-size: 16px; font-weight: bold; margin-bottom: 2px;'>📊 TRẠM PHÂN TÍCH DIỆN MẠO NHÀ KÍNH & ĐỀ XUẤT ĐIỀU HÀNH</p>", unsafe_allow_html=True)
            selected_report_day = st.selectbox("Chọn ngày tổng kết để xem phân tích:", list(st.session_state.daily_reports.keys()))
            st.dataframe(st.session_state.daily_reports[selected_report_day], use_container_width=True, hide_index=True)

    # --- CONTAINER 6: BIỂU ĐỒ XU HƯỚNG TƯƠNG TÁC (ĐÃ SỬA LỖI ĐỊNH DẠNG TRỤC X) ---
    if len(st.session_state.history) > 0:
        st.write("")
        with st.container(border=True):
            st.markdown("<p style='color: gray; font-size: 14px; margin-bottom: 2px;'>📈 BIỂU ĐỒ XU HƯỚNG ĐỒNG BỘ CHU KỲ (Xoay chuột để Zoom)</p>", unsafe_allow_html=True)
            df_chart = pd.DataFrame(st.session_state.history).iloc[::-1]
            
            tab_temp, tab_rh, tab_vpd = st.tabs(["🌡️ Biểu đồ Nhiệt độ", "💧 Biểu đồ Độ ẩm", "🎯 Biểu đồ chỉ số VPD"])
            with tab_temp:
                chart_temp = alt.Chart(df_chart).mark_line(color="#FF4B4B", point=True).encode(
                    x=alt.X('Thời gian mô phỏng:T', axis=alt.Axis(title="Mốc thời gian", format='%H:%M')), # SỬA: :T thay cho :O để chạy được .interactive()
                    y=alt.Y('Nhiệt độ (°C):Q', scale=alt.Scale(zero=False)),
                    tooltip=['Ngày', 'Hiển thị Giờ', 'Nhiệt độ (°C)']
                ).properties(height=260).interactive()
                st.altair_chart(chart_temp, use_container_width=True)
            with tab_rh:
                chart_rh = alt.Chart(df_chart).mark_line(color="#0068C9", point=True).encode(
                    x=alt.X('Thời gian mô phỏng:T', axis=alt.Axis(title="Mốc thời gian", format='%H:%M')), # SỬA: :T thay cho :O
                    y=alt.Y('Độ ẩm (%):Q', scale=alt.Scale(zero=False)),
                    tooltip=['Ngày', 'Hiển thị Giờ', 'Độ ẩm (%)']
                ).properties(height=260).interactive()
                st.altair_chart(chart_rh, use_container_width=True)
            with tab_vpd:
                bg_data = pd.DataFrame([{'start_blue': 0.0, 'end_blue': vpd_min, 'start_red': vpd_max, 'end_red': 3.0}])
                rect_blue = alt.Chart(bg_data).mark_rect(color='#0068C9', opacity=0.15).encode(y=alt.Y('start_blue:Q'), y2=alt.Y2('end_blue:Q'))
                rect_red = alt.Chart(bg_data).mark_rect(color='#FF4B4B', opacity=0.15).encode(y=alt.Y('start_red:Q'), y2=alt.Y2('end_red:Q'))
                line_vpd = alt.Chart(df_chart).mark_line(color="#2E7D32", point=True).encode(
                    x=alt.X('Thời gian mô phỏng:T', axis=alt.Axis(title="Mốc thời gian", format='%H:%M')), # SỬA: :T thay cho :O
                    y=alt.Y('VPD (kPa):Q', scale=alt.Scale(domain=[0, 3.0])),
                    tooltip=['Ngày', 'Hiển thị Giờ', 'VPD (kPa)', 'Trạng thái']
                )
                st.altair_chart((rect_blue + rect_red + line_vpd).properties(height=260).interactive(), use_container_width=True)

    # --- CONTAINER 7: LỊCH SỬ DỮ LIỆU BẢNG ---
    st.write("")
    with st.container(border=True):
        st.markdown("<p style='color: gray; font-size: 14px; margin-bottom: 10px;'>📋 LỊCH SỬ DỮ LIỆU ĐÃ GHI NHẬN</p>", unsafe_allow_html=True)
        if len(st.session_state.history) > 0:
            # Tạo bản sao hiển thị để rút gọn cột thời gian dạng chuỗi xuông dễ nhìn trên bảng
            df_display = pd.DataFrame(st.session_state.history).copy()
            df_display["Thời gian mô phỏng"] = df_display["Hiển thị Giờ"]
            df_display = df_display.drop(columns=["Hiển thị Giờ"])
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.write("Chưa có dữ liệu lịch sử.")
        
        if st.button("""🗑️ Xóa lịch sử""", type="secondary"):
            st.session_state.stt_counter = 0
            st.session_state.temp = 0.0
            st.session_state.rh = 0.0
            st.session_state.history = []
            st.session_state.daily_reports = {}
            st.session_state.simulated_time = "2026-05-24 07:00:00"
            st.rerun()

# Chạy Dashboard
vpd_controlled_monitor()
