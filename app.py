import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime, timedelta

from calculations import calculate_vpd, get_weather_by_time
from services import send_telegram_message, get_quick_solution
from analytics import (
    analyze_day_by_blocks_rt, 
    predict_vpd_trend_v3, 
    calculate_plant_stress_hours, 
    calculate_dew_point, 
    get_biological_block
)
from charts import draw_temperature_chart, draw_humidity_chart, draw_vpd_chart

TELE_TOKEN = "8917951413:AAE6LKUEfYEYiQrFWGoKsQn0tumZc_XbcHg"
TELE_CHAT_ID = "7290661009"

st.set_page_config(page_title="VPD Smart Farm Monitor Pro", page_icon="🌿", layout="wide")

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { overflow-y: auto !important; scroll-behavior: smooth; }
    .block-container { padding-top: 1rem; padding-bottom: 2rem; padding-left: 1.5rem; padding-right: 1.5rem; }
    .danger-box-red { padding: 12px; background-color: #FFEBEE; border-left: 6px solid #FF1744; color: #B71C1C; font-weight: bold; border-radius: 4px; margin-bottom: 8px; }
    .danger-box-blue { padding: 12px; background-color: #E3F2FD; border-left: 6px solid #2979FF; color: #0D47A1; font-weight: bold; border-radius: 4px; margin-bottom: 8px; }
    .upload-header { font-size: 15px; font-weight: bold; color: #1A5276; border-bottom: 2px solid #D4E6F1; padding-bottom: 4px; margin-bottom: 10px; }
    .metric-card-upload { background-color: #F4F6F7; border: 1px solid #E5E7E9; padding: 10px; border-radius: 6px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# Khởi tạo Session State
if 'temp' not in st.session_state: st.session_state.temp = 0.0
if 'rh' not in st.session_state: st.session_state.rh = 0.0
if 'countdown' not in st.session_state: st.session_state.countdown = 15 
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'is_completed' not in st.session_state: st.session_state.is_completed = False 
if 'history' not in st.session_state: st.session_state.history = []
if 'stt_counter' not in st.session_state: st.session_state.stt_counter = 0 
if 'simulated_time' not in st.session_state: st.session_state.simulated_time = "2026-05-24 07:00:00"
if 'automation_webhook' not in st.session_state: st.session_state.automation_webhook = ""

# Ngưỡng cây trồng mẫu mặc định cố định
PRESETS = {
    "🍓 Dâu tây Đà Lạt (Giai đoạn trái)": (0.6, 1.1),
    "🌹 Hoa hồng nhà kính": (0.8, 1.4),
    "🍅 Cà chua bi / Ớt chuông": (0.7, 1.3),
    "🌱 Cây giống vườn ươm": (0.4, 0.8)
}

def style_status_rows(row):
    styles = [''] * len(row)
    status = str(row['Trạng thái'])
    if "Lý tưởng" in status: styles[row.index.get_loc('Trạng thái')] = 'background-color: #E8F5E9; color: #1B5E20; font-weight: bold;'
    elif "Quá khô" in status: styles[row.index.get_loc('Trạng thái')] = 'background-color: #FFEBEE; color: #B71C1C; font-weight: bold;'
    elif "Quá ẩm" in status: styles[row.index.get_loc('Trạng thái')] = 'background-color: #E3F2FD; color: #0D47A1; font-weight: bold;'
    return styles

def trigger_new_data(v_min, v_max):
    current_sim_datetime = datetime.strptime(st.session_state.simulated_time, "%Y-%m-%d %H:%M:%S")
    current_date_str = current_sim_datetime.strftime("Ngày %d/%m")
    st.session_state.temp, st.session_state.rh = get_weather_by_time(current_sim_datetime)
    st.session_state.countdown = 15 
    st.session_state.stt_counter += 1
    new_vpd = calculate_vpd(st.session_state.temp, st.session_state.rh)
    
    status_text = "⚠️ Quá ẩm" if new_vpd < v_min else ("✅ Lý tưởng" if new_vpd <= v_max else "🚨 Quá khô")
    
    st.session_state.history.insert(0, {
        "STT": st.session_state.stt_counter, "Ngày": current_date_str,
        "Thời gian mô phỏng": current_sim_datetime, "Hiển thị Giờ": current_sim_datetime.strftime("%H:%M"),
        "datetime_internal": current_sim_datetime, "Nhiệt độ (°C)": st.session_state.temp, "Độ ẩm (%)": st.session_state.rh,
        "VPD (kPa)": round(new_vpd, 2), "Trạng thái": status_text
    })
    
    if st.session_state.automation_webhook:
        try: requests.post(st.session_state.automation_webhook, json={"vpd": new_vpd, "status": status_text}, timeout=2)
        except: pass

    if TELE_TOKEN and TELE_CHAT_ID:
        unique_days = sorted(list(set([r["Ngày"] for r in st.session_state.history])), reverse=True)
        h_latest = [r for r in st.session_state.history if r["Ngày"] == (unique_days[0] if unique_days else current_date_str)]
        trend, trend_type = predict_vpd_trend_v3(h_latest, current_sim_datetime.hour, v_min, v_max)
        buoi_hien_tai = get_biological_block(current_sim_datetime.hour)
        
        msg = (f"🌿 *VPD MONITOR REALTIME*\n⏰ {current_date_str} - {current_sim_datetime.strftime('%H:%M')} ({buoi_hien_tai})\n"
               f"📊 Môi trường: {st.session_state.temp}°C | {st.session_state.rh}%\n"
               f"*VPD thực tế:* *{new_vpd:.2f} kPa* (Ngưỡng đích: {v_min}-{v_max} kPa)\n"
               f"📢 *Hiện trạng:* {status_text}\n🔮 *Dự báo:* _{trend}_")
        send_telegram_message(TELE_TOKEN, TELE_CHAT_ID, msg)
    
    next_dt = current_sim_datetime + timedelta(minutes=10)
    if next_dt.hour == 0 and next_dt.minute == 0:
        st.session_state.is_running = False; st.session_state.is_completed = True   
    st.session_state.simulated_time = next_dt.strftime("%Y-%m-%d %H:%M:%S")

# Mồi dữ liệu ban đầu
if 'vpd_range_val' not in st.session_state:
    st.session_state.vpd_range_val = (0.6, 1.1)

if st.session_state.stt_counter == 0: 
    trigger_new_data(st.session_state.vpd_range_val[0], st.session_state.vpd_range_val[1])

tab_future, tab_past, tab_edge = st.tabs(["🔮 MÔ PHỎNG & XEM REALTIME", "📁 QUÉT FILE IOT HỆ THỐNG", "⚙️ CẤU HÌNH WEBHOOK TỰ ĐỘNG"])

with tab_edge:
    st.markdown("### ⚙️ HỆ THỐNG ĐIỀU KHIỂN VÒNG LẶP KÍN (CLOSED-LOOP AUTOMATION)")
    st.session_state.automation_webhook = st.text_input("Địa chỉ API Webhook kích hoạt relay phần cứng tủ điện nhà kính:", value=st.session_state.automation_webhook)

# --------------------------------------------------------
# TAB 1: MÔ PHỎNG SỐ LIỆU REALTIME
# --------------------------------------------------------
with tab_future:
    left_col, right_col = st.columns([4, 6])
    with left_col:
        st.markdown("<h3 style='color: #2E7D32; font-size: 17px;'>📋 CẤU HÌNH NGƯỠNG VPD THEO GIỐNG CÂY</h3>", unsafe_allow_html=True)
        preset_choice = st.selectbox("Chọn nhanh cấu hình chuẩn nông nghiệp:", list(PRESETS.keys()) + ["🛠️ Tùy chỉnh thủ công dải"])
        
        if preset_choice != "🛠️ Tùy chỉnh thủ công dải":
            st.session_state.vpd_range_val = PRESETS[preset_choice]
            st.slider("Dải VPD Lý tưởng mục tiêu (kPa):", min_value=0.0, max_value=3.0, value=st.session_state.vpd_range_val, step=0.1, key="slider_disabled", disabled=True)
        else:
            st.session_state.vpd_range_val = st.slider("Dải VPD Lý tưởng mục tiêu (kPa):", min_value=0.0, max_value=3.0, value=st.session_state.vpd_range_val, step=0.1, key="slider_enabled")

        vpd_min, vpd_max = st.session_state.vpd_range_val

        with st.container(border=True):
            c_b1, c_b2 = st.columns(2)
            with c_b1:
                if st.button("▶️ Khởi chạy trạm", type="primary", use_container_width=True):
                    if st.session_state.is_completed: 
                        st.session_state.simulated_time = "2026-05-24 07:00:00"
                        st.session_state.is_completed = False
                    st.session_state.is_running = True
                    st.rerun()
            with c_b2:
                if st.button("⏸️ Tạm dừng trạm", type="secondary", use_container_width=True):
                    st.session_state.is_running = False
                    st.rerun()

        run_interval = 1 if st.session_state.is_running else 999999
        @st.fragment(run_every=run_interval)
        def live_monitor_panel():
            if st.session_state.is_running:
                st.session_state.countdown -= 1
                if st.session_state.countdown < 0: 
                    trigger_new_data(vpd_min, vpd_max)
                    st.rerun()
            
            sim_dt = datetime.strptime(st.session_state.simulated_time, "%Y-%m-%d %H:%M:%S")
            with st.container(border=True):
                st.markdown(f"⏰ **Mốc thời gian:** `{sim_dt.strftime('%d/%m/%Y — %H:%M')}` | ⏳ **Đếm ngược chu kỳ:** `{st.session_state.countdown}s`")
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("🌡️ Nhiệt độ khí", f"{st.session_state.temp}°C")
                col_m2.metric("💧 Độ ẩm khí", f"{st.session_state.rh}%")
                
                v_calc = calculate_vpd(st.session_state.temp, st.session_state.rh)
                dp_calc = calculate_dew_point(st.session_state.temp, st.session_state.rh)
                
                st.markdown(f"📊 **VPD Hiện tại:** ` {v_calc:.2f} kPa ` | 🥶 *Điểm đọng sương lá:* `{dp_calc} °C`")
        live_monitor_panel()

        if st.session_state.history:
            st.markdown("### 🛠️ KHUYẾN NGHỊ ĐIỀU KHIỂN PHẦN CỨNG LẬP TỨC")
            cur_v = st.session_state.history[0]["VPD (kPa)"]
            solution = get_quick_solution(cur_v, vpd_min, vpd_max)
            if "QUÁ KHÔ" in solution: st.markdown(f"<div class='danger-box-red'>{solution}</div>", unsafe_allow_html=True)
            elif "QUÁ ẨM" in solution: st.markdown(f"<div class='danger-box-blue'>{solution}</div>", unsafe_allow_html=True)
            else: st.success(solution)

    with right_col:
        st.markdown("<h3 style='color: #2E7D32; font-size: 17px;'>📊 PHÂN TÍCH DIỄN BIẾN CHU KỲ PHÒNG DỊCH</h3>", unsafe_allow_html=True)
        if not st.session_state.history:
            st.info("Hệ thống đang tích lũy dữ liệu chu kỳ trạm.")
        else:
            u_days = sorted(list(set([r["Ngày"] for r in st.session_state.history])), reverse=True)
            sel_day = st.selectbox("Chọn ngày lịch sử xem lại:", u_days, label_visibility="collapsed")
            df_all = pd.DataFrame(st.session_state.history)
            df_f = df_all[df_all["Ngày"] == sel_day].iloc[::-1].copy()
            
            m_tab1, m_tab2 = st.tabs(["📈 Đồ thị biến động", "📋 Bảng nhật ký chi tiết"])
            with m_tab1:
                st.altair_chart(draw_vpd_chart(df_f, vpd_min, vpd_max), use_container_width=True)
            with m_tab2:
                st.dataframe(df_f[["STT", "Hiển thị Giờ", "Nhiệt độ (°C)", "Độ ẩm (%)", "VPD (kPa)", "Trạng thái"]].style.apply(style_status_rows, axis=1), use_container_width=True, hide_index=True)

# --------------------------------------------------------
# TAB 2: TẢI FILE & KHỚP 1 NGƯỠNG CỐ ĐỊNH BAN ĐẦU
# --------------------------------------------------------
with tab_past:
    st.markdown("<h3 style='color: #1A5276; font-size: 18px;'>📁 TẢI FILE NHẬT KÝ IOT TRẠM CẢM BIẾN</h3>", unsafe_allow_html=True)
    f_left, f_right = st.columns([4, 6])
    
    with f_left:
        with st.container(border=True):
            st.markdown("<div class='upload-header'>🌿 THIẾT LẬP NGƯỠNG ÁP DỤNG TRÊN FILE</div>", unsafe_allow_html=True)
            f_preset_choice = st.selectbox("Chọn cấu hình chuẩn áp vào file dữ liệu:", list(PRESETS.keys()) + ["🛠️ Tùy chỉnh thủ công dải"], key="sb_file")
            if 'file_range_val' not in st.session_state: st.session_state.file_range_val = (0.6, 1.1)
            
            if f_preset_choice != "🛠️ Tùy chỉnh thủ công dải":
                st.session_state.file_range_val = PRESETS[f_preset_choice]
                st.slider("Dải mục tiêu:", min_value=0.0, max_value=3.0, value=st.session_state.file_range_val, step=0.1, key="sl_file_dis", disabled=True)
            else:
                st.session_state.file_range_val = st.slider("Dải mục tiêu:", min_value=0.0, max_value=3.0, value=st.session_state.file_range_val, step=0.1, key="sl_file_en")
                
            f_vpd_min, f_vpd_max = st.session_state.file_range_val
            
    with f_right:
        with st.container(border=True):
            st.markdown("<div class='upload-header'>📥 CHỌN TẢI FILE & CHẾ ĐỘ LỘC GỘP</div>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Kéo thả file IoT (.json, .csv, .xlsx) của trạm cảm biến:", type=["json", "csv", "xlsx"])
            time_filter_option = st.selectbox(
                "📆 Cấu hình lọc dữ liệu theo khoảng chu kỳ thời gian:",
                ["📊 Xem toàn bộ dữ liệu gốc của File", "📆 Tự chọn một ngày cụ thể trên lịch", "⏱️ 1 Ngày gần nhất (Gom trung bình 10 phút)", "📅 1 Tuần gần nhất (Gộp trung bình 1 Ngày / 1 Điểm)"]
            )
        
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.json'):
                json_data = json.load(uploaded_file)
                df_upload = pd.DataFrame([json_data]) if isinstance(json_data, dict) and not isinstance(list(json_data.values())[0], (dict, list)) else pd.DataFrame(json_data)
            elif uploaded_file.name.endswith('.csv'):
                df_upload = pd.read_csv(uploaded_file)
            else:
                df_upload = pd.read_excel(uploaded_file)
                
            col_temp, col_rh, col_time = None, None, None
            for col in df_upload.columns:
                col_lower = str(col).lower().strip()
                if 'tempkk' in col_lower: col_temp = col
                if 'humikk' in col_lower: col_rh = col
                if any(k in col_lower for k in ['thời gian', 'time', 'gio', 'date', 'timestamp', 'mốc', 'created_at']): col_time = col

            if not col_temp:
                for col in df_upload.columns:
                    col_lower = str(col).lower().strip()
                    if any(k in col_lower for k in ['temp', 'nhiet', 't°', 'temperature']): col_temp = col
            if not col_rh:
                for col in df_upload.columns:
                    col_lower = str(col).lower().strip()
                    if any(k in col_lower for k in ['rh', 'hum', 'do am', 'humidity']): col_rh = col

            if not col_temp and len(df_upload.columns) > 0: col_temp = df_upload.columns[0]
            if not col_rh and len(df_upload.columns) > 1: col_rh = df_upload.columns[1]
            if not col_time and len(df_upload.columns) > 2: col_time = df_upload.columns[2]

            raw_datetimes = []
            for val in df_upload[col_time].astype(str):
                cleaned_val = val.strip()
                try:
                    if " " in cleaned_val and "-" in cleaned_val.split(" ")[1]:
                        date_p, time_p = cleaned_val.split(" ")
                        raw_datetimes.append(datetime.strptime(f"{date_p} {time_p.replace('-', ':')}", "%Y-%m-%d %H:%M:%S"))
                    else:
                        raw_datetimes.append(pd.to_datetime(cleaned_val))
                except:
                    raw_datetimes.append(datetime.now())

            df_raw_calc = pd.DataFrame()
            df_raw_calc["datetime_internal"] = raw_datetimes
            
            raw_temp_series = pd.to_numeric(df_upload[col_temp], errors='coerce')
            df_raw_calc["Nhiệt độ (°C)"] = raw_temp_series.apply(lambda x: x / 10.0 if pd.notna(x) and x >= 45.0 else x)
            df_raw_calc["Độ ẩm (%)"] = pd.to_numeric(df_upload[col_rh], errors='coerce').apply(lambda x: x / 100.0 if pd.notna(x) and x > 100.0 else x)
            
            df_raw_calc = df_raw_calc[df_raw_calc["Độ ẩm (%)"] > 1.0].dropna().sort_values("datetime_internal")
            df_raw_calc["VPD_raw"] = df_raw_calc.apply(lambda row: calculate_vpd(row["Nhiệt độ (°C)"], row["Độ ẩm (%)"]), axis=1)
            df_raw_calc["only_date"] = df_raw_calc["datetime_internal"].dt.date
            available_dates = sorted(df_raw_calc["only_date"].unique())
            
            if "Tự chọn một ngày cụ thể" in time_filter_option:
                selected_date = st.date_input("👇 Chọn ngày trích xuất dữ liệu trên lịch:", value=available_dates[-1] if available_dates else datetime.now().date())
                df_raw_calc = df_raw_calc[df_raw_calc["only_date"] == selected_date]
            elif "1 Ngày gần nhất" in time_filter_option:
                df_raw_calc = df_raw_calc[df_raw_calc["datetime_internal"] >= (df_raw_calc["datetime_internal"].max() - timedelta(days=1))]
            elif "1 Tuần gần nhất" in time_filter_option:
                df_raw_calc = df_raw_calc[df_raw_calc["datetime_internal"] >= (df_raw_calc["datetime_internal"].max() - timedelta(days=7))]

            df_for_block_analysis = df_raw_calc.copy()

            if len(df_raw_calc) > 0:
                unique_days_filtered = df_raw_calc["only_date"].nunique()
                df_resample_input = df_raw_calc[["datetime_internal", "Nhiệt độ (°C)", "Độ ẩm (%)", "VPD_raw"]].copy()
                df_resample_input.set_index("datetime_internal", inplace=True)
                
                if "1 Tuần gần nhất" in time_filter_option:
                    df_resampled = df_resample_input.resample("1D").mean().dropna()
                elif "1 Ngày gần nhất" in time_filter_option or "Xem toàn bộ dữ liệu gốc" in time_filter_option:
                    df_resampled = df_resample_input.resample("10min").mean().dropna() if unique_days_filtered <= 2 else df_resample_input.resample("1h").mean().dropna()
                else:
                    df_resampled = df_resample_input.copy()
                
                df_resampled["datetime_internal"] = df_resampled.index
                df_resampled["Hiển thị Giờ"] = df_resampled["datetime_internal"].dt.strftime("%d/%m %H:%M") if unique_days_filtered > 2 else df_resampled["datetime_internal"].dt.strftime("%H:%M")
                df_resampled.reset_index(drop=True, inplace=True)
            else:
                unique_days_filtered = 0
                df_resampled = pd.DataFrame(columns=["datetime_internal", "Nhiệt độ (°C)", "Độ ẩm (%)", "VPD_raw", "Hiển thị Giờ"])

            df_processed = pd.DataFrame()
            df_processed["datetime_internal"] = df_resampled["datetime_internal"]
            df_processed["Nhiệt độ (°C)"] = df_resampled["Nhiệt độ (°C)"].round(2)
            df_processed["Độ ẩm (%)"] = df_resampled["Độ ẩm (%)"].round(2)
            df_processed["VPD (kPa)"] = df_resampled["VPD_raw"].round(2)
            df_processed["Hiển thị Giờ"] = df_resampled["Hiển thị Giờ"]
            df_processed["Ngày"] = "Dữ liệu File"
            df_processed["Trạng thái"] = df_processed["VPD (kPa)"].apply(lambda v: "⚠️ Quá ẩm" if v < f_vpd_min else ("✅ Lý tưởng" if v <= f_vpd_max else "🚨 Quá khô"))

            st.markdown("<div style='margin-top:12px; margin-bottom:5px; font-weight:bold; color:#1A5276;'>📊 TỔNG QUAN CHU KỲ SAU KHI GỘP SỐ LIỆU FILE</div>", unsafe_allow_html=True)
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.markdown(f"<div class='metric-card-upload'><span style='font-size:12px;color:grey;'>📈 VPD TRUNG BÌNH</span><br><b style='font-size:18px;color:#2E7D32;'>{df_processed['VPD (kPa)'].mean():.2f} kPa</b></div>", unsafe_allow_html=True)
            m_col2.markdown(f"<div class='metric-card-upload'><span style='font-size:12px;color:grey;'>🌡️ NHIỆT ĐỘ TRUNG BÌNH</span><br><b style='font-size:18px;color:#FF4B4B;'>{df_processed['Nhiệt độ (°C)'].mean():.1f} °C</b></div>", unsafe_allow_html=True)
            m_col3.markdown(f"<div class='metric-card-upload'><span style='font-size:12px;color:grey;'>💧 ĐỘ ẨM TRUNG BÌNH</span><br><b style='font-size:18px;color:#0068C9;'>{df_processed['Độ ẩm (%)'].mean():.1f} %</b></div>", unsafe_allow_html=True)
            m_col4.markdown(f"<div class='metric-card-upload'><span style='font-size:12px;color:grey;'>📋 SỐ ĐIỂM BIỂU ĐỒ</span><br><b style='font-size:18px;color:#5D6D7E;'>{len(df_processed)} điểm</b></div>", unsafe_allow_html=True)

            adv_res = calculate_plant_stress_hours(df_processed, f_vpd_min, f_vpd_max, time_filter_option)
            st.markdown("<div style='margin-top:15px; font-weight:bold; color:#B71C1C;'>⚠️ ĐÁNH GIÁ CHUYÊN SÂU: ÁP LỰC STRESS KHÍ KHỔNG CỦA CÂY TRỒNG</div>", unsafe_allow_html=True)
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                d_hrs = adv_res["dry_hours"]
                if d_hrs > 2.0: st.error(f"🚨 **Stress Khô Nóng:** Khí khổng bị ép khép chặt suốt **{d_hrs} giờ**. Cây ngừng quang hợp, có nguy cơ cháy lá hoa!")
                else: st.success(f"✅ **Áp lực khô:** An toàn (Chỉ có {d_hrs} giờ bị vượt ngưỡng khô gắt).")
            with s_col2:
                w_hrs = adv_res["wet_hours"]
                if w_hrs > 4.0: st.warning(f"🟦 **Stress Ẩm Ướt:** Môi trường tích tụ đọng ẩm liên tục **{w_hrs} giờ**. Nguy cơ bùng dịch nấm phấn trắng và sương mai!")
                else: st.success(f"✅ **Áp lực ẩm:** An toàn (Chỉ có {w_hrs} giờ đọng ẩm nằm ngoài dải).")

            st.markdown("#### 🍄 DỰ BÁO PHẦN TRĂM NGUY CƠ DỊCH NẤM ĐÀ LẠT")
            risk_val = adv_res['fungus_risk']
            if risk_val < 30: st.success(f"🟢 Mức độ rủi ro dịch bệnh THẤP ({risk_val}%). Thích hợp bón lá dinh dưỡng.")
            elif risk_val < 70: st.warning(f"🟡 Mức độ rủi ro TRUNG BÌNH ({risk_val}%). Bào tử nấm bắt đầu mọc mầm, bật quạt thông gió ngay!")
            else: st.error(f"🔴 CẢNH BÁO NGUY HIỂM CAO ({risk_val}%). Điều kiện lý tưởng bùng phát dịch nấm phấn trắng diện rộng!")
            st.progress(risk_val / 100.0)

            res_left, res_right = st.columns([6.2, 3.8])
            with res_left:
                st.markdown("<div style='font-weight:bold; color:#1A5276; margin-bottom:5px;'>📈 CÁC BIỂU ĐỒ ĐỐI CHIẾU TRỰC QUAN</div>", unsafe_allow_html=True)
                f_tab1, f_tab2, f_tab3 = st.tabs(["🎯 Chỉ số VPD", "🌡️ Nhiệt độ khí", "💧 Độ ẩm khí"])
                with f_tab1: st.altair_chart(draw_vpd_chart(df_processed, f_vpd_min, f_vpd_max), use_container_width=True)
                with f_tab2: st.altair_chart(draw_temperature_chart(df_processed), use_container_width=True)
                with f_tab3: st.altair_chart(draw_humidity_chart(df_processed), use_container_width=True)
            with res_right:
                st.markdown("<div style='font-weight:bold; color:#1A5276; margin-bottom:5px;'>📋 NHẬT KÝ ĐIỂM GỘP CHU KỲ CHUYÊN SÂU</div>", unsafe_allow_html=True)
                preview_cols = ["Hiển thị Giờ", "Nhiệt độ (°C)", "Độ ẩm (%)", "VPD (kPa)", "Trạng thái"]
                st.dataframe(df_processed[preview_cols].style.apply(style_status_rows, axis=1), use_container_width=True, hide_index=True, height=270)
                
                st.download_button(
                    label="📥 Xuất báo cáo tính toán chu kỳ ma trận (.csv)",
                    data=df_processed.to_csv(index=False).encode('utf-8'),
                    file_name=f"vpd_matrix_periodic_report.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            st.markdown("---")
            st.markdown(f"##### 📊 BÁO CÁO PHÂN TÍCH TỔNG HỢP THEO BUỔI CHU KỲ (Dữ liệu gốc từ File)")
            if len(df_for_block_analysis) > 0:
                df_block_report = analyze_day_by_blocks_rt(df_for_block_analysis.assign(Ngày="Dữ liệu File"), f_vpd_min, f_vpd_max, "Dữ liệu File")
                st.dataframe(df_block_report, use_container_width=True, hide_index=True)
                
                if st.button("📤 Gửi báo cáo ma trận qua Telegram", type="primary", key="btn_send_file_tele"):
                    if TELE_TOKEN and TELE_CHAT_ID:
                        file_tele_msg = f"📂 *BÁO CÁO PHÂN TÍCH CHU KỲ FILE*\n📦 File: `{uploaded_file.name}`\n🎯 Mô hình: *{f_preset_choice}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
                        for _, r_data in df_block_report.iterrows():
                            icon_status = "🟩" if "Lý tưởng" in r_data["Đánh giá sinh học"] else ("🟦" if "Quá ẩm" in r_data["Đánh giá sinh học"] else "🟥")
                            file_tele_msg += f"{icon_status} *{r_data['Khoảng Buổi']}*\n▪️ Môi trường: {r_data['Nhiệt độ TB']} | {r_data['Độ ẩm TB']}\n▪️ VPD TB: *{r_data['VPD Trung Bình']}*\n▪️ Đánh giá: _{r_data['Đánh giá sinh học']}_\n▪️ Giải pháp: {r_data['Giải pháp kỹ thuật']}\n────────────────────\n"
                        file_tele_msg += f"\n📊 _Hệ thống tự động chấm điểm sinh học VPD Smart Farm_"
                        success = send_telegram_message(TELE_TOKEN, TELE_CHAT_ID, file_tele_msg)
                        if success: st.success("✅ Đã gửi toàn bộ dữ liệu báo cáo qua Telegram thành công!")
            else:
                st.info("Chưa có đủ dữ liệu thích hợp để bóc tách chu kỳ buổi.")

        except Exception as err:
            st.error(f"❌ Không thể xử lý cấu trúc file. Lỗi chi tiết: {err}")
    else:
        st.info("💡 Hệ thống tự động bóc tách dữ liệu thông minh: Vui lòng kéo thả file log IoT của bạn vào ô phía trên để bắt đầu phân tích chu kỳ đối chiếu ma trận.")
