import streamlit as st
import pandas as pd
import numpy as np
import paho.mqtt.client as mqtt
import requests
import json
import time

# Cấu hình giao diện di động
st.set_page_config(page_title="Hệ Thống MQTT Real-Time", page_icon="🚨", layout="centered")

st.title("🚨 Hệ Thống VPD Real-Time Qua MQTT")
st.markdown("Ứng dụng đang nghe tín hiệu trực tiếp từ cảm biến qua giao thức **MQTT 30 giây/lần**. Cấu hình thanh trượt để đổi ngưỡng cảnh báo động.")

# --- CẤU HÌNH THÔNG TIN KẾT NỐI ĐỒNG BỘ VỚI NODE GIẢ LẬP ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "vuon_thong_minh/duy_tran/sensors"
TELEGRAM_TOKEN = "8537718260:AAFtydsQNB8mnGQ51Tt15rlu4dBKjJcGGWU"   
TELEGRAM_CHAT_ID = "7290661009"                                     

# --- KHỞI TẠO BỘ NHỚ LƯU TRỮ TẠM THỜI TRÊN APP (STATE) ---
if "mqtt_df" not in st.session_state:
    st.session_state.mqtt_df = pd.DataFrame()

# =====================================================================
# CẤU HÌNH THANH TRƯỢT NGƯỠNG ĐỘNG
# =====================================================================
st.subheader("⚙️ Cài Đặt Ngưỡng VPD")
low_threshold = st.slider("1. Ngưỡng VPD Thấp (Quá ẩm):", min_value=0.1, max_value=1.0, value=0.4, step=0.05, format="%.2f kPa")
high_threshold = st.slider("2. Ngưỡng VPD Cao (Khô nóng):", min_value=1.0, max_value=3.0, value=1.2, step=0.05, format="%.2f kPa")
mid_threshold = round((low_threshold + high_threshold) / 2, 2)

# =====================================================================
# LOGIC VẬN HÀNH TOÁN HỌC VÀ BOT TELEGRAM
# =====================================================================

def calculate_vpd(temp, humi):
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    return np.clip(vp_sat * (1 - (humi / 100)), 0, None)

def send_telegram_auto(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=3)
    except: pass

def analyze_realtime_and_trigger_bot(vpd, temp, humi, station_id, time_log):
    sid = str(station_id)
    if humi == 0:
        msg = f"🔌 *MẤT TÍN HIỆU THIẾT BỊ*\n⏱ Cập nhật: {time_log}\n📍 Vị trí: Trạm {sid}\n📝 *Lý do:* Độ ẩm đột ngột tụt về 0%.\n🛠 *Hành động:* Ra vườn kiểm tra lại cục cảm biến ngay!"
        send_telegram_auto(msg)
        return pd.Series(["Mất tín hiệu thiết bị", f"Trạm {sid} báo độ ẩm bằng 0%.", "Kiểm tra lại dây nguồn, giắc nối đầu dò."])
    
    if vpd > high_threshold and temp > 40.0 and humi < 40.0:
        msg = f"🔥 *BÁO ĐỘNG MQTT REAL-TIME: KHÔ NÓNG GẮT*\n⏱ Cập nhật: {time_log}\n📍 Vị trí: Trạm {sid}\n🌡 Nhiệt độ: {temp}°C | 💧 Độ ẩm: {humi}%\n💨 *VPD thực tế:* {vpd} kPa\n🛠 *Hành động:* CHẠY RA KÉO LƯỚI LAN ĐEN CẤT NẮNG, BẬT PHUN SƯƠNG BÙ ẨM KHẨN CẤP!"
        send_telegram_auto(msg)
        return pd.Series(["⚠️ CẢNH BÁO: KHÔ NÓNG GẮT", f"Trạm {sid} vượt ngưỡng khô gắt cài đặt ({vpd} kPa).", "CHẠY RA KÉO LƯỚI LAN ĐEN CẤT NẮNG, BẬT PHUN SƯƠNG BÙ ẨM KHẨN CẤP!"])
        
    if humi >= 99.5 or vpd == 0:
        msg = f"⚠️ *THÔNG BÁO: BÃO HÒA ẨM*\n⏱ Cập nhật: {time_log}\n📍 Vị trí: Trạm {sid}\n💧 Độ ẩm chạm trần: {humi}%\n🛠 *Hành động:* Bật ngay quạt hút đuổi ẩm và ngừng tưới nước ngay!"
        send_telegram_auto(msg)
        return pd.Series(["Không khí ẩm ướt bão hòa", f"Trạm {sid} báo độ ẩm chạm trần {humi}%.", "Bật ngay quạt hút đuổi ẩm và ngừng tưới nước!"])

    if vpd < low_threshold:
        return pd.Series(["Nhà kính quá ẩm", f"VPD thấp hơn mốc cài đặt ({vpd} < {low_threshold} kPa).", "Bật quạt đối lưu, mở cửa hông để thoát bớt hơi ẩm."])
    if low_threshold <= vpd < mid_threshold:
        return pd.Series(["Môi trường mát mẻ lý tưởng", f"VPD nằm trong khoảng ẩm dịu ngọt ({vpd} kPa).", "Mọi thứ bình thường. Tiếp tục duy trì."])
    if mid_threshold <= vpd <= high_threshold:
        return pd.Series(["Thời tiết hoàn hảo", f"VPD đạt điểm vàng quang hợp ({vpd} kPa).", "Thời điểm vàng nuôi quả lớn. Giữ nguyên chế độ vườn."])
    
    if humi < 40.0:
        return pd.Series(["Môi trường khô hanh", f"VPD vượt ngưỡng nhẹ ({vpd} kPa).", "Bật hệ thống phun sương giữa vườn để bù lại độ ẩm."])
    else:
        return pd.Series(["Nhiệt độ tăng cao", f"Nhiệt độ nhà màng hầm nóng ({temp}°C).", "Tăng thời gian tưới nhỏ giọt dưới gốc cấp nước cho rễ."])

# --- CƠ CHẾ LẮNG NGHE MQTT ĐỒNG BỘ (MQTT SUBSCRIBER) ---
def on_message(client, userdata, message):
    try:
        payload_str = message.payload.decode("utf-8")
        new_data = json.loads(payload_str)
        df_new = pd.DataFrame(new_data)
        # Nối đuôi dữ liệu mới nhận qua mạng vào bộ nhớ tạm của App
        if st.session_state.mqtt_df.empty:
            st.session_state.mqtt_df = df_new
        else:
            st.session_state.mqtt_df = pd.concat([st.session_state.mqtt_df, df_new], ignore_index=True)
    except:
        pass

# Thiết lập bộ nhận tín hiệu chạy ngầm trên trang Web của Streamlit
@st.cache_resource
def start_mqtt_client():
    mqtt_client = mqtt.Client()
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.subscribe(MQTT_TOPIC)
    mqtt_client.loop_start()
    return mqtt_client

# Kích hoạt trạm thu sóng MQTT ngầm
_ = start_mqtt_client()

# --- XỬ LÝ ĐỔ DỮ LIỆU RA MÀN HÌNH ĐIỆN THOẠI ---
df = st.session_state.mqtt_df.copy()

if not df.empty:
    time_col = 'Thời gian' if 'Thời gian' in df.columns else 'time'
    stt_col = 'STT' if 'STT' in df.columns else 'station'
    
    df[time_col] = df[time_col].astype(str)
    df[stt_col] = df[stt_col].astype(str)
    df = df.sort_values(by=time_col, ascending=True)
    
    latest_time_log = df[time_col].iloc[-1]
    st.markdown(f"⏱️ **Mốc MQTT vừa nhận từ ruộng:** `{latest_time_log}`")
    st.subheader("🔔 Nhật Ký Theo Dõi Cảm Biến Real-Time")
    
    processed_chunks = []
    # Chỉ bóc tách dòng mới nhất vừa bay qua sóng MQTT để xử lý trạng thái
    for station_id in df[stt_col].unique():
        row = df[df[stt_col] == station_id].tail(1).iloc[0]
        t_col = 'tempKK' if station_id == "5" else ('Nhiệt Độ' if 'Nhiệt Độ' in df.columns else 'Nhiệt độ')
        h_col = 'humiKK' if station_id == "5" else 'Độ ẩm'
        
        if t_col in df.columns and h_col in df.columns and not pd.isna(row[t_col]) and not pd.isna(row[h_col]):
            t_val = pd.to_numeric(row[t_col])
            h_val = pd.to_numeric(row[h_col])
            if station_id != "5" and t_val > 100: t_val /= 10.0
            if station_id != "5" and h_val > 100: h_val /= 10.0
            
            vpd_val = calculate_vpd(t_val, h_val).round(3)
            result_series = analyze_realtime_and_trigger_bot(vpd_val, t_val, h_val, station_id, latest_time_log)
            
            processed_chunks.append(pd.DataFrame([{
                "Thời gian": latest_time_log,
                "Số Trạm": station_id,
                "VPD (kPa)": vpd_val,
                "Trạng Thái Vườn": result_series[0],
                "Lý Do Từ Cảm Biến": result_series[1],
                "Hành Động Khắc Phục": result_series[2]
            }]))
            
    if processed_chunks:
        st.dataframe(pd.concat(processed_chunks, ignore_index=True), use_container_width=True)

else:
    st.info("🔌 Hệ thống đang mở cổng sóng, chờ file giả lập `simulation_node.py` bắn dữ liệu MQTT qua mạng...")

# Vòng lặp 30 giây đồng bộ để nạp dữ liệu từ sóng MQTT lên màn hình
time.sleep(30)
st.rerun()
