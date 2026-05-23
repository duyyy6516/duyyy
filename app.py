import streamlit as st
import random
import math
from datetime import datetime, timedelta
import pandas as pd
import altair as alt
import requests

# =================================================================
# ⚙️ CẤU HÌNH BẢO MẬT TELEGRAM ĐÃ GHIM CỐ ĐỊNH (ẨN KHỎI GIAO DIỆN)
# =================================================================
TELE_TOKEN = "8917951413:AAE6LKUEfYEYiQrFWGoKsQn0tumZc_XbcHg"
TELE_CHAT_ID = "8924137204"
# =================================================================

# Cấu hình trang web Streamlit
st.set_page_config(page_title="Hệ thống giám sát VPD Đà Lạt", page_icon="🌿", layout="centered")

# --- TIÊU ĐỀ CHÍNH ---
st.markdown("<h2 style='text-align: center; color: #2E7D32;'>🌿 HỆ THỐNG GIÁM SÁT & TÍNH TOÁN VPD ĐÀ LẠT</h2>", unsafe_allow_html=True)
st.write("")

# --- HÀM GỬI THÔNG BÁO QUA TELEGRAM BOT ---
def send_telegram_message(token, chat_id, message):
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

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

# --- HÀM TRA CỨU GIẢI PHÁP REALTIME NHANH THEO TIẾNG ---
def get_quick_solution(vpd_val, vpd_min, vpd_max, hour):
    if vpd_val < vpd_min: # Quá ẩm
        if 7 <= hour < 11:
            return "Mở bạt hông muộn hoặc bật quạt gió để xua tan sương ẩm ban đêm đọng trên lá."
        elif 11 <= hour < 19:
            return "Trời ẩm u hoặc có mưa. Bật quạt đối lưu mạnh, đóng vách ngăn nước mưa và hạn chế tưới gốc dầm dề."
        else:
            return "Ẩm độ ban đêm rất cao. Tuyệt đối không tưới muộn sau 16h; bật thông gió định kỳ."
    elif vpd_min <= vpd_val <= vpd_max: # Lý tưởng
        return "Môi trường hoàn hảo. Duy trì chế độ thông thoáng tự nhiên và lịch tưới hiện tại của nhà kính."
    else: # Quá khô
        if 7 <= hour < 11:
            return "Nắng lên nhanh làm nhiệt tăng. Kích hoạt nhẹ tưới nhỏ giọt để cấp ẩm vùng rễ."
        elif 11 <= hour < 15:
            return "Cao điểm nắng nóng! Kéo lưới đen cắt nắng (giảm 30%), phun sương mịn định kỳ 5-10 phút/lần."
        elif 15 <= hour < 19:
            return "Nhiệt muộn vẫn cao. Bổ sung một lượt phun sương ngắn để hạ nhiệt trước khi đóng vách kính."
        else:
            return "Hiện tượng nhiệt tăng bất thường ban đêm. Kiểm tra thiết bị sưởi hoặc đóng kín vách ngăn gió."

# --- HÀM PHÂN TÍCH THỜI GIAN THỰC THEO BUỔI ---
def analyze_day_by_blocks_rt(history_list, vpd_min, vpd_max, target_date_str):
    day_data = [r for r in history_list if r["Nancy"] == target_date_str] if "Nancy" in pd.DataFrame(history_list).columns else [r for r in history_list if r["Ngày"] == target_date_str]
    
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
                if "Sáng" in block_name: huong_xu_ly = "Mở bạt hông muộn hoặc bật quạt gió để xua tan sương ẩm ban đêm đọng trên lá."
                elif "Trưa" in block_name or "Chiều" in block_name: huong_xu_ly = "Trời ẩm u/mưa khép vách. Bật quạt đối lưu mạnh, hạn chế tưới gốc dầm dề."
                else: huong_xu_ly = "Ẩm độ ban đêm rất cao. Tuyệt đối không tưới muộn sau 16h; bật thông gió định kỳ."
            elif vpd_min <= avg_vpd <= vpd_max:
                danh_gia = "🟩 Lý tưởng"
                huong_xu_ly = "Môi trường hoàn hảo. Duy trì chế độ thông thoáng tự nhiên và lịch tưới hiện tại."
            else:
                danh_gia = "🟥 Quá khô"
                if "Sáng" in block_name: huong_xu_ly = "Nắng lên nhanh làm nhiệt tăng. Kích hoạt nhẹ tưới nhỏ giọt để cấp ẩm vùng rễ."
                elif "Trưa" in block_name: huong_xu_ly = "Cao điểm nắng nóng! Kéo lưới đen cắt nắng (giảm 30%), phun sương mịn 5-10 phút/lần."
                elif "Chiều" in block_name: huong_xu_ly = "Nhiệt muộn vẫn cao. Bổ sung một lượt phun sương ngắn để hạ nhiệt trước khi đóng vách."
                else: huong_xu_ly = "Hiện tượng bất thường ban đêm. Kiểm tra thiết bị sưởi hoặc đóng kín vách ngăn gió."
            
            summary.append({
                "Khoảng Thời Gian": block_name,
                "VPD TB (kPa)": round(avg_vpd, 2),
                "Đánh Giá": danh_gia,
                "Hướng Xử Lý Đề Xuất (Kỹ thuật nhà kính)": huong_xu_ly
            })
        else:
            summary.append({
                "Khoảng Thời Gian": block_name,
                "VPD TB (kPa)": "--",
                "Đánh Giá": "⚪ Đang chờ mốc giờ...",
                "Hướng Xử Lý Đề Xuất (Kỹ thuật nhà kính)": "Chưa có dữ liệu thu thập cho buổi này."
            })
    return pd.DataFrame(summary)

# --- HÀM DỰ BÁO XU HƯỚNG CHU KỲ THỜI TIẾT TỰ NHIÊN ---
def predict_vpd_trend_v3(filtered_history, current_hour):
    if len(filtered_history) < 2:
        return "🔄 Hệ thống đang tích lũy số liệu mốc giờ để tính toán...", "info"
        
    if 7 <= current_hour < 11:
        return "Nắng đang lên nhanh, bức xạ mặt trời tăng mạnh. Dự báo nhiệt độ tiếp tục tăng và độ ẩm sẽ giảm sâu trong các mốc giờ tới.", "warning"
    elif 11 <= current_hour < 14:
        return "Đang ở đỉnh điểm bức xạ trong ngày. Dự báo môi trường sẽ duy trì trạng thái khô nóng cực hạn trước khi dịu dần sau 14h30.", "error"
    elif 14 <= current_hour < 18:
        return "Nắng đang tắt dần, bức xạ nhiệt suy giảm. Dự báo nhiệt độ nhà kính sẽ hạ nhanh và ẩm độ bắt đầu đảo chiều tăng mạnh.", "success"
    else:
        return "Giai đoạn đêm và rạng sáng. Không có bức xạ mặt trời, nhiệt độ tiếp tục hạ thấp và độ ẩm sẽ bão hòa tiến sát mốc 95%.", "info"

# --- KHỔI TẠO BIẾN TRONG SESSION STATE ---
if 'temp' not in st.session_state: st.session_state.temp = 0.0
if 'rh' not in st.session_state: st.session_state.rh = 0.0
if 'countdown' not in st.session_state: st.session_state.countdown = 15 
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'is_completed' not in st.session_state: st.session_state.is_completed = False 
if 'history' not in st.session_state: st.session_state.history = []
if 'stt_counter' not in st.session_state: st.session_state.stt_counter = 0 

if 'simulated_time' not in st.session_state:
    st.session_state.simulated_time = "2026-05-24 07:00:00"

# --- THANH CẤU HÌNH SIDEBAR (CỘT TRÁI) ---
with st.sidebar:
    st.markdown("<h3 style='color: #2E7D32;'>⚙️ BẢN ĐIỀU KHIỂN CẤU HÌNH</h3>", unsafe_allow_html=True)
    
    plant_option = st.selectbox(
        "Chọn loại cây trồng canh tác:",
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

    st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
    st.success("🤖 Hệ thống Telegram Bot: Đã được kích hoạt ngầm bằng Token cá nhân của bạn thành công!")

# --- HÀM TẠO LẬP NGÀY MỚI KHI BẤM CHẠY TIẾP ---
def setup_next_day():
    current_dt = datetime.strptime(st.session_state.simulated_time, "%Y-%m-%d %H:%M:%S")
    if current_dt.hour == 0 and current_dt.minute == 0:
        next_day_dt = current_dt + timedelta(hours=7)
    else:
        next_day_dt = current_dt + timedelta(days=1)
        next_day_dt = next_day_dt.replace(hour=7, minute=0, second=0)
        
    st.session_state.simulated_time = next_day_dt.strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.is_completed = False
    st.session_state.countdown = 15

# --- HÀM CẬP NHẬT DỮ LIỆU MỚI (TÍCH HỢP TỰ ĐỘNG BẮN TELEGRAM) ---
def trigger_new_data(vpd_min, vpd_max, token, chat_id):
    current_sim_datetime = datetime.strptime(st.session_state.simulated_time, "%Y-%m-%d %H:%M:%S")
    current_date_str = current_sim_datetime.strftime("Ngày %d/%m")
    
    st.session_state.temp, st.session_state.rh = get_weather_by_time(current_sim_datetime)
    st.session_state.countdown = 15 
    st.session_state.stt_counter += 1
    new_vpd = calculate_vpd(st.session_state.temp, st.session_state.rh)
    
    if new_vpd < vpd_min:
        status_text = "⚠️ Quá ẩm"
        tele_status = "🟦 QUÁ ẨM"
    elif vpd_min <= new_vpd <= vpd_max:
        status_text = "✅ Lý tưởng"
        tele_status = "🟩 LÝ TƯỞNG"
    else:
        status_text = "🚨 Quá khô"
        tele_status = "🟥 QUÁ KHÔ"
    
    new_record = {
        "STT": st.session_state.stt_counter,
        "Ngày": current_date_str,
        "Thời gian mô phỏng": current_sim_datetime,
        "Hiển thị Giờ": current_sim_datetime.strftime("%H:%M"),
        "Nhiệt độ (°C)": st.session_state.temp,
        "Độ ẩm (%)": st.session_state.rh,
        "VPD (kPa)": round(new_vpd, 2),
        "Trạng thái": status_text
    }
    st.session_state.history.insert(0, new_record)
    
    # 📱 TỰ ĐỘNG GỬI TIN NHẮN THEO CẤU HÌNH CỨNG TRONG CODE
    if token and chat_id:
        sol = get_quick_solution(new_vpd, vpd_min, vpd_max, current_sim_datetime.hour)
        unique_days = sorted(list(set([r["Ngày"] for r in st.session_state.history])), reverse=True)
        latest_day_in_db = unique_days[0] if unique_days else current_date_str
        history_of_latest_day = [r for r in st.session_state.history if r["Ngày"] == latest_day_in_db]
        trend, _ = predict_vpd_trend_v3(history_of_latest_day, current_sim_datetime.hour)
        
        # Tin nhắn cấu trúc 3 dòng gọn gàng đổ thẳng về điện thoại
        telegram_msg = (
            f"🌿 *HỆ THỐNG VPD ĐÀ LẠT REALTIME*\n"
            f"⏰ Thời gian: {current_date_str} - {current_sim_datetime.strftime('%H:%M')}\n"
            f"📊 Môi trường: {st.session_state.temp}°C | {st.session_state.rh}%\n\n"
            f"*1️⃣ Trạng thái hệ thống:* Chỉ số đạt *{new_vpd:.2f} kPa* —— Phân loại: *{tele_status}*\n"
            f"*2️⃣ Hướng giải pháp đề xuất:* _{sol}_\n"
            f"*3️⃣ Xu hướng vận hành tiếp theo:* {trend}"
        )
        send_telegram_message(token, chat_id, telegram_msg)
    
    next_sim_datetime = current_sim_datetime + timedelta(minutes=30)
    
    if next_sim_datetime.hour == 0 and next_sim_datetime.minute == 0:
        st.session_state.is_running = False     
        st.session_state.is_completed = True   
        st.session_state.simulated_time = next_sim_datetime.strftime("%Y-%m-%d %H:%M:%S")
    else:
        st.session_state.simulated_time = next_sim_datetime.strftime("%Y-%m-%d %H:%M:%S")

# --- CONTAINER 2: KHU VỰC ĐIỀU KHIỂN & ĐỒNG HỒ ---
with st.container(border=True):
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("""▶️ Bắt đầu chạy tự động""", type="primary", use_container_width=True, disabled=st.session_state.is_running):
            if st.session_state.is_completed:
                setup_next_day()
            st.session_state.is_running = True
            if st.session_state.stt_counter == 0: 
                trigger_new_data(vpd_min, vpd_max, TELE_TOKEN, TELE_CHAT_ID)
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
        if st.session_state.countdown < 0: 
            trigger_new_data(vpd_min, vpd_max, TELE_TOKEN, TELE_CHAT_ID)
            st.rerun()
            
    if st.session_state.is_running:
        st.write(f"⏳ Tự động đổi số sau: **{st.session_state.countdown}** giây")
        st.progress(st.session_state.countdown / 15)
    elif st.session_state.is_completed:
        st.success("🏁 Đã chạy xong 1 ngày trọn vẹn! Hãy nhấn nút 'Bắt đầu' lần nữa để hệ thống TỰ ĐỘNG CHUYỂN SANG NGÀY TIẾP THEO.")
    else:
        st.info("💡 Hệ thống đang tạm dừng.")

    current_sim_dt = datetime.strptime(st.session_state.simulated_time, "%Y-%m-%d %H:%M:%S")
    current_date_display = current_sim_dt.strftime("Ngày %d/%m")
    
    # --- CONTAINER 3: THÔNG SỐ REALTIME HÌNH THỨC ---
    st.write("")
    with st.container(border=True):
        st.markdown(f"### ⏰ Thời gian nhà kính hiện tại: <span style='color:#2E7D32;'>{current_date_display} - {current_sim_dt.strftime('%H:%M')}</span>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: st.metric(label="🌡️ Nhiệt độ", value=f"{st.session_state.temp} °C" if st.session_state.stt_counter > 0 else "-- °C")
        with col2: st.metric(label="💧 Độ ẩm", value=f"{st.session_state.rh} %" if st.session_state.stt_counter > 0 else "-- %")

    # --- ĐỊNH DẠNG THEO THỨ TỰ YÊU CẦU: TRẠNG THÁI -> GIẢI PHÁP -> XU HƯỚNG ---
    vpd_result = calculate_vpd(st.session_state.temp, st.session_state.rh)
    st.write("")
    with st.container(border=True):
        st.markdown("<p style='color: #2E7D32; font-size: 16px; font-weight: bold; margin-bottom: 8px;'>🎯 HỆ THỐNG PHÂN TÍCH & ĐIỀU HÀNH VPD REALTIME</p>", unsafe_allow_html=True)
        
        if st.session_state.stt_counter == 0:
            st.info("📊 Đang chờ hệ thống bắt đầu kích hoạt phát số...")
        else:
            if vpd_result < vpd_min:
                status_lbl = "🟦 QUÁ ẨM"
                text_color = "#0068C9"
            elif vpd_min <= vpd_result <= vpd_max:
                status_lbl = "🟩 LÝ TƯỞNG"
                text_color = "#2E7D32"
            else:
                status_lbl = "🟥 QUÁ KHÔ"
                text_color = "#FF4B4B"
                
            unique_days = sorted(list(set([r["Ngày"] for r in st.session_state.history])), reverse=True)
            latest_day_in_db = unique_days[0] if unique_days else current_date_display
            history_of_latest_day = [r for r in st.session_state.history if r["Ngày"] == latest_day_in_db]
            
            sol_text = get_quick_solution(vpd_result, vpd_min, vpd_max, current_sim_dt.hour)
            trend_msg, msg_type = predict_vpd_trend_v3(history_of_latest_day, current_sim_dt.hour)
            
            st.markdown(f"**1️⃣ Trạng thái hệ thống:** Chỉ số hiện tại đạt <span style='font-size: 16px; color: {text_color}; font-weight: bold;'>{vpd_result:.2f} kPa</span> —— Phân loại: **{status_lbl}**", unsafe_allow_html=True)
            st.markdown(f"**2️⃣ Hướng giải pháp đề xuất:** *{sol_text}*")
            st.markdown(f"**3️⃣ Xu hướng vận hành tiếp theo:** {trend_msg}")
            
            st.markdown("<p style='color: #0088cc; font-size: 12px; font-style: italic; margin-top: 5px;'>🚀 Tin nhắn bảo mật 3 dòng đang được gửi tự động và đồng bộ ngầm về Telegram của bạn!</p>", unsafe_allow_html=True)

    # --- BỘ LỌC LƯU TRỮ TRUNG TÂM ---
    if len(st.session_state.history) > 0:
        st.write("")
        with st.container(border=True):
            st.markdown("<p style='color: #2E7D32; font-size: 16px; font-weight: bold; margin-bottom: 2px;'>🗂️ BỘ LỌC LƯU TRỮ LỊCH SỬ NHÀ KÍNH</p>", unsafe_allow_html=True)
            unique_days = sorted(list(set([r["Ngày"] for r in st.session_state.history])), reverse=True)
            selected_view_day = st.selectbox("Chọn ngày lịch sử cần kiểm tra (Biểu đồ và Bảng số liệu sẽ đồng bộ theo ngày này):", unique_days)
            
            df_all_records = pd.DataFrame(st.session_state.history)
            df_filtered = df_all_records[df_all_records["Ngày"] == selected_view_day].iloc[::-1].copy()

        # --- CONTAINER 5: BÁO CÁO PHÂN TÍCH THEO BUỔI CỦA NGÀY ĐƯỢC CHỌN ---
        st.write("")
        with st.container(border=True):
            st.markdown(f"<p style='color: #2E7D32; font-size: 15px; font-weight: bold; margin-bottom: 2px;'>📊 TRẠM PHÂN TÍCH THEO BUỔI & ĐỀ XUẤT ĐIỀU HÀNH ({selected_view_day})</p>", unsafe_allow_html=True)
            rt_report_df = analyze_day_by_blocks_rt(st.session_state.history, vpd_min, vpd_max, selected_view_day)
            st.dataframe(rt_report_df, use_container_width=True, hide_index=True)

        # --- CONTAINER 6: HỆ THỐNG BIỂU ĐỒ ĐÃ ĐƯỢC LỌC THEO NGÀY CHỌN ---
        st.write("")
        with st.container(border=True):
            st.markdown(f"<p style='color: gray; font-size: 14px; margin-bottom: 2px;'>📈 BIỂU ĐỒ XU HƯỚNG THEO CHU KỲ - LỌC: {selected_view_day}</p>", unsafe_allow_html=True)
            
            tab_temp, tab_rh, tab_vpd, tab_combined = st.tabs(["🌡️ Biểu đồ Nhiệt độ", "💧 Biểu đồ Độ ẩm", "🎯 Biểu đồ chỉ số VPD", "📊 Biểu đồ Tổ hợp 3 chỉ số"])
            
            with tab_temp:
                chart_temp = alt.Chart(df_filtered).mark_line(color="#FF4B4B", point=True).encode(
                    x=alt.X('Hiển thị Giờ:O', axis=alt.Axis(title="Mốc thời gian", labelAngle=0)), 
                    y=alt.Y('Nhiệt độ (°C):Q', scale=alt.Scale(zero=False), axis=alt.Axis(title="Nhiệt độ (°C)")),
                    tooltip=['Ngày', 'Hiển thị Giờ', 'Nhiệt độ (°C)']
                ).properties(height=260).interactive()
                st.altair_chart(chart_temp, use_container_width=True)
                
            with tab_rh:
                chart_rh = alt.Chart(df_filtered).mark_line(color="#0068C9", point=True).encode(
                    x=alt.X('Hiển thị Giờ:O', axis=alt.Axis(title="Mốc thời gian", labelAngle=0)),
                    y=alt.Y('Độ ẩm (%):Q', scale=alt.Scale(zero=False), axis=alt.Axis(title="Độ ẩm (%)")),
                    tooltip=['Ngày', 'Hiển thị Giờ', 'Độ ẩm (%)']
                ).properties(height=260).interactive()
                st.altair_chart(chart_rh, use_container_width=True)
                
            with tab_vpd:
                st.caption(f"ℹ️ Vùng màu an toàn theo [{plant_option}]: 🟦 Quá ẩm (< {vpd_min} kPa) | 🟥 Quá khô (> {vpd_max} kPa)")
                bg_data = pd.DataFrame([{'start_blue': 0.0, 'end_blue': vpd_min, 'start_red': vpd_max, 'end_red': 3.0}])
                
                rect_blue = alt.Chart(bg_data).mark_rect(color='#0068C9', opacity=0.12).encode(
                    y=alt.Y('start_blue:Q', scale=alt.Scale(domain=[0, 3.0])), 
                    y2=alt.Y2('end_blue:Q')
                )
                rect_red = alt.Chart(bg_data).mark_rect(color='#FF4B4B', opacity=0.12).encode(
                    y=alt.Y('start_red:Q', scale=alt.Scale(domain=[0, 3.0])), 
                    y2=alt.Y2('end_red:Q')
                )
                line_vpd = alt.Chart(df_filtered).mark_line(color="#2E7D32", point=True).encode(
                    x=alt.X('Hiển thị Giờ:O', axis=alt.Axis(title="Mốc thời gian", labelAngle=0)),
                    y=alt.Y('VPD (kPa):Q', scale=alt.Scale(domain=[0, 3.0]), axis=alt.Axis(title="Chỉ số VPD (kPa)", grid=True)),
                    tooltip=['Ngày', 'Hiển thị Giờ', 'VPD (kPa)', 'Trạng thái']
                ).interactive() 
                
                chart_vpd = (rect_blue + rect_red + line_vpd).properties(height=260)
                st.altair_chart(chart_vpd, use_container_width=True)

            with tab_combined:
                st.caption("🔴 Đường Đỏ: Nhiệt độ (°C) | 🔵 Đường Xanh dương: Độ ẩm (%) [Trục Trái] --- 🟢 Đường Xanh lá: VPD (kPa) [Trục Phải]")
                base = alt.Chart(df_filtered).encode(
                    x=alt.X('Hiển thị Giờ:O', axis=alt.Axis(title="Mốc thời gian", labelAngle=0))
                )
                line_t = base.mark_line(color='#FF4B4B', strokeDash=[3,3], point=alt.OverlayMarkDef(color='#FF4B4B')).encode(
                    y=alt.Y('Nhiệt độ (°C):Q', axis=alt.Axis(title="Nhiệt độ (°C) / Độ ẩm (%)", titleColor='#0068C9')),
                    tooltip=['Hiển thị Giờ', 'Nhiệt độ (°C)']
                )
                line_r = base.mark_line(color='#0068C9', point=alt.OverlayMarkDef(color='#0068C9')).encode(
                    y=alt.Y('Độ ẩm (%):Q'),
                    tooltip=['Hiển thị Giờ', 'Độ ẩm (%)']
                )
                weather_layer = alt.layer(line_t, line_r)
                line_v = base.mark_line(color='#2E7D32', size=3, point=alt.OverlayMarkDef(color='#2E7D32')).encode(
                    y=alt.Y('VPD (kPa):Q', axis=alt.Axis(title="Áp suất VPD (kPa)", titleColor='#2E7D32'), scale=alt.Scale(domain=[0, 3.0])),
                    tooltip=['Hiển thị Giờ', 'VPD (kPa)', 'Trạng thái']
                )
                combined_chart = alt.layer(weather_layer, line_v).properties(height=260).resolve_scale(
                    y='independent'
                ).interactive()
                st.altair_chart(combined_chart, use_container_width=True)

        # --- CONTAINER 7: LỊCH SỬ BẢNG ĐÃ ĐƯỢC LỌC ---
        st.write("")
        with st.container(border=True):
            st.markdown(f"<p style='color: gray; font-size: 14px; margin-bottom: 10px;'>📋 BẢNG LỊCH SỬ GHI NHẬN - LỌC: {selected_view_day}</p>", unsafe_allow_html=True)
            df_display = df_filtered.iloc[::-1].copy() 
            df_display["Thời gian mô phỏng"] = df_display["Hiển thị Giờ"]
            df_display = df_display.drop(columns=["Hiển thị Giờ"])
            st.dataframe(df_display, use_container_width=True, hide_index=True)

        # NÚT XÓA SẠCH DATABASE HỆ THỐNG
        if st.button("""🗑️ Khởi động lại hệ thống (Xóa toàn bộ dữ liệu lịch sử)""", type="secondary"):
            st.session_state.stt_counter = 0
            st.session_state.temp = 0.0
            st.session_state.rh = 0.0
            st.session_state.history = []
            st.session_state.simulated_time = "2026-05-24 07:00:00"
            st.session_state.is_completed = False
            st.session_state.is_running = False
            st.rerun()

# Khởi chạy Dashboard
vpd_controlled_monitor()
