import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

# =====================================================================
# 1. CẤU HÌNH CONFIG BOT ZALO (ĐÃ ĐỒNG BỘ THEO TÀI KHOẢN DUY)
# =====================================================================
# Dán chính xác chuỗi Access Token siêu dài lấy từ hình ảnh API Explorer vào đây:
ZALO_ACCESS_TOKEN = "JhN_GvCLKoL7j_j0a11K9Ks--q674Gjt4_2aLSyXJs4QXO0y4nrT2RqAAwscLVrbh0RxqKumS6dOQvS..."
# Dán chuỗi Refresh Token ở hàng thứ hai trong ảnh dán vào đây:
ZALO_REFRESH_TOKEN = "I2Dl7bBJ-tsr8MiTKTRyVRyeQnn6XgG--79c67Rbe1MPHpKt9kkdEBLYQnSxFmAaNiS5GVgqHQN7W..."
# ID tài khoản Zalo cá nhân Duy bạn vừa lấy được từ lệnh v2.0/me
ZALO_USER_ID = "6669070447643778989"

def send_zalo_bot_official(message):
    """
    Hàm gọi OpenAPI Zalo gửi tin nhắn trực tiếp về số điện thoại Duy.
    Đã tích hợp cơ chế tự động gia hạn token khi hết hạn (Sau 1 tiếng).
    """
    global ZALO_ACCESS_TOKEN, ZALO_REFRESH_TOKEN
    
    url = "https://openapi.zalo.me/v2.0/me/message"
    headers = {
        "access_token": ZALO_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    # Định dạng tin nhắn gửi qua tài khoản nhà phát triển (Dạng text thuần sạch đẹp)
    payload = {
        "recipient": {
            "user_id": ZALO_USER_ID
        },
        "message": {
            "text": message.replace("*", "").replace("`", "").replace("_", "")
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        result = response.json()
        
        # Gửi thành công
        if result.get("error") == 0 or "message_id" in result:
            st.success("🔔 Đã bắn thông báo trạng thái trạm về Zalo!")
            
        # Lỗi hết hạn Token -> Tiến hành tự động gia hạn bằng Refresh Token
        elif result.get("error") in [-216, -203] or "expired" in result.get("message", "").lower():
            refresh_url = "https://oauth.zalo.chat/v2/access_token"
            refresh_headers = {
                "secret_key": "477V5VQFUCDRS8lGlI7R",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            refresh_data = {
                "app_id": "509634047731079806",
                "grant_type": "refresh_token",
                "refresh_token": ZALO_REFRESH_TOKEN
            }
            
            refresh_res = requests.post(refresh_url, data=refresh_data, headers=refresh_headers, timeout=5).json()
            
            if "access_token" in refresh_res:
                ZALO_ACCESS_TOKEN = refresh_res["access_token"]
                ZALO_REFRESH_TOKEN = refresh_res["refresh_token"]
                
                # Thử gửi lại tin nhắn bằng token mới tinh vừa đổi
                headers["access_token"] = ZALO_ACCESS_TOKEN
                requests.post(url, json=payload, headers=headers, timeout=5)
                st.success("🔄 Đã tự động gia hạn Token Zalo và gửi lại tin nhắn thành công!")
            else:
                st.error(f"❌ Gia hạn Token Zalo thất bại: {refresh_res.get('error_description')}")
        else:
            st.error(f"❌ Zalo trả về mã lỗi: {result.get('message')} (Mã: {result.get('error')})")
            
    except Exception as e:
        st.error(f"❌ Lỗi đường truyền kết nối Zalo: {e}")

# =====================================================================
# 2. LOGIC TOÁN HỌC VÀ ĐÁNH GIÁ TRẠNG THÁI VPD
# =====================================================================
def calculate_vpd(temp, humi):
    """
    Công thức toán học tính áp suất hơi bão hòa và độ hụt áp suất hơi (VPD)
    """
    # Áp suất hơi bão hòa VPsat (kPa) dựa trên nhiệt độ
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    # Độ hụt áp suất hơi VPD (kPa) dựa trên độ ẩm thực tế
    vpd = vp_sat * (1 - (humi / 100))
    return float(np.clip(vpd, 0, None))

def evaluate_station_status(temp, humi, vpd):
    """
    Phân tích trạng thái sức khỏe của cây trồng dựa vào chỉ số VPD
    """
    if pd.isna(temp) or pd.isna(humi):
        return "⚠️ Mất tín hiệu cảm biến", "inverse"
    elif vpd < 0.4:
        return "❌ BÁO ĐỘNG: Nguy cơ nấm bệnh (VPD quá thấp)", "danger"
    elif 0.4 <= vpd < 0.8:
        return "🟡 Cảnh báo nhẹ: Hơi ẩm", "warning"
    elif 0.8 <= vpd <= 1.2:
        return "✅ Môi trường lý tưởng cho cây phát triển", "success"
    elif 1.2 < vpd <= 1.6:
        return "🟡 Cảnh báo nhẹ: Hơi khô", "warning"
    else:
        return "❌ BÁO ĐỘNG: Cây bị stress nhiệt (VPD quá cao)", "danger"

# =====================================================================
# 3. GIAO DIỆN STREAMLIT VÀ VÒNG QUÉT DỮ LIỆU TỰ ĐỘNG
# =====================================================================
st.set_page_config(page_title="Hệ Thống Giám Sát VPD Vườn - Zalo", layout="wide")
st.title("🌿 Hệ Thống Giám Sát Chỉ Số VPD Thông Minh - 5 Trạm Vườn")
st.write("Dữ liệu tự động cập nhật liên tục. Trạng thái bất thường sẽ tự động báo về Zalo.")

# Cấu hình tự động refresh ứng dụng (Ví dụ cài đặt: 30 giây làm mới 1 lần)
# st_autorefresh(interval=30000, key="datamonitor")

# Hàm mô phỏng lấy dữ liệu từ phần cứng/API IoT trạm vườn gửi về
def fetch_iot_garden_data():
    # Giả lập dữ liệu ngẫu nhiên cho 5 trạm vườn để kiểm thử
    np.random.seed(int(time.time()))
    data = {
        "Trạm Vườn": ["Trạm 1 (Khu A)", "Trạm 2 (Khu B)", "Trạm 3 (Khu C)", "Trạm 4 (Khu D)", "Trạm 5 (Khu E)"],
        "Nhiệt độ (°C)": np.round(np.random.uniform(22.0, 35.0, 5), 1),
        "Độ ẩm (%)": np.round(np.random.uniform(40.0, 95.0, 5), 1)
    }
    return pd.DataFrame(data)

# Thực thi lấy dữ liệu hiện tại
df_garden = fetch_iot_garden_data()

# Tính toán các cột chỉ số VPD và Trạng thái tự động dựa trên dữ liệu thật
df_garden["VPD (kPa)"] = df_garden.apply(lambda row: round(calculate_vpd(row["Nhiệt độ (°C)"], row["Độ ẩm (%)"]), 2), axis=1)

# Thiết lập cấu trúc giao diện hiển thị 5 trạm dạng lưới (Cards) trực quan
cols = st.columns(5)
zalo_alert_messages = []

for idx, row in df_garden.iterrows():
    status_text, style = evaluate_station_status(row["Nhiệt độ (°C)"], row["Độ ẩm (%)"], row["VPD (kPa)"])
    
    with cols[idx]:
        st.markdown(f"### {row['Trạm Vườn']}")
        st.metric(label="🌡️ Nhiệt độ", value=f"{row['Nhiệt độ (°C)']} °C")
        st.metric(label="💧 Độ ẩm", value=f"{row['Độ ẩm (%)']} %")
        st.metric(label="📊 Chỉ số VPD", value=f"{row['VPD (kPa)']} kPa")
        
        # Hiển thị màu sắc trạng thái tương ứng trên giao diện Streamlit
        if style == "success":
            st.success(status_text)
        elif style == "warning":
            st.warning(status_text)
        elif style == "danger":
            st.error(status_text)
            # Nếu phát hiện trạng thái BÁO ĐỘNG (Nguy hiểm), gộp nội dung gửi tin về Zalo
            zalo_alert_messages.append(f"- {row['Trạm Vườn']}: T={row['Nhiệt độ (°C)']}°C, H={row['Độ ẩm (%)']}%, VPD={row['VPD (kPa)']}kPa -> {status_text}")
        else:
            st.info(status_text)

st.markdown("---")
st.markdown("### 📋 Bảng Dữ Liệu Tổng Hợp 5 Trạm Vườn")
st.dataframe(df_garden, use_container_width=True)

# =====================================================================
# 4. KÍCH HOẠT GỬI TIN BÁO QUA ZALO KHI PHÁT HIỆN BẤT THƯỜNG
# =====================================================================
if zalo_alert_messages:
    # Gom tất cả các trạm bị lỗi báo động vào một tin nhắn tổng hợp để tránh spam tin nhắn
    final_zalo_msg = "⚠️ HỆ THỐNG CẢNH BÁO VƯỜN DUY TRẦN:\n" + "\n".join(zalo_alert_messages)
    
    # Kiểm tra tránh gửi lặp tin nhắn giống nhau liên tục bằng session_state
    if "last_alert_content" not in st.session_state or st.session_state.last_alert_content != final_zalo_msg:
        send_zalo_bot_official(final_zalo_msg)
        st.session_state.last_alert_content = final_zalo_msg
else:
    st.info("✅ Hiện tại tất cả 5 trạm vườn đều đang hoạt động trong ngưỡng an toàn ổn định.")
