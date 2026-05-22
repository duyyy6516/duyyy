import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

# =====================================================================
# 1. CẤU HÌNH CONFIG BOT ZALO (ĐÃ ĐỒNG BỘ THEO TÀI KHOẢN DUY)
# =====================================================================
# Khởi tạo hoặc giữ cấu hình Token Zalo bảo mật v4
if "ZALO_ACCESS_TOKEN" not in st.session_state:
    st.session_state.ZALO_ACCESS_TOKEN = "JhN_GvCLKoL7j_j0a11K9Ks--q674Gjt4_2aLSyXJs4QXO0y4nrT2RqAAwscLVrbh0RxqKumS6dOQvS..."

if "ZALO_REFRESH_TOKEN" not in st.session_state:
    st.session_state.ZALO_REFRESH_TOKEN = "I2Dl7bBJ-tsr8MiTKTRyVRyeQnn6XgG--79c67Rbe1MPHpKt9kkdEBLYQnSxFmAaNiS5GVgqHQN7W..."

# ID tài khoản Zalo cá nhân Duy lấy từ lệnh v2.0/me
ZALO_USER_ID = "6669070447643778989"
ZALO_APP_ID = "509634047731079806"
ZALO_SECRET_KEY = "477V5VQFUCDRS8lGlI7R"

def send_zalo_bot_official(message):
    """
    Hàm gọi OpenAPI Zalo gửi tin nhắn trực tiếp về số điện thoại Duy.
    Đã nâng cấp cơ chế Timeout lên 10s, tự động thử lại và tự gia hạn Token.
    """
    url = "https://openapi.zalo.me/v2.0/me/message"
    
    headers = {
        "access_token": st.session_state.ZALO_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    # Định dạng tin nhắn thuần túy, sạch ký tự đặc biệt để hiển thị đẹp trên Zalo
    payload = {
        "recipient": {
            "user_id": ZALO_USER_ID
        },
        "message": {
            "text": message.replace("*", "").replace("`", "").replace("_", "")
        }
    }
    
    # Cơ chế vòng lặp thử lại tối đa 2 lần đề phòng mạng chập chờn
    for attempt in range(2):
        try:
            # Tăng timeout lên 10 giây để an toàn hơn khi server Zalo phản hồi chậm
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            result = response.json()
            
            # TRƯỜNG HỢP 1: Gửi thành công
            if result.get("error") == 0 or "message_id" in result:
                st.success("🔔 Đã bắn thông báo trạng thái trạm về Zalo thành công!")
                break
                
            # TRƯỜNG HỢP 2: Lỗi hết hạn Token (Mã -216, -203) -> Tiến hành tự động gia hạn
            elif result.get("error") in [-216, -203] or "expired" in result.get("message", "").lower():
                print("🔄 Access Token hết hạn! Đang tiến hành tự động gia hạn qua Refresh Token...")
                
                refresh_url = "https://oauth.zalo.chat/v2/access_token"
                refresh_headers = {
                    "secret_key": ZALO_SECRET_KEY,
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                refresh_data = {
                    "app_id": ZALO_APP_ID,
                    "grant_type": "refresh_token",
                    "refresh_token": st.session_state.ZALO_REFRESH_TOKEN
                }
                
                refresh_res = requests.post(refresh_url, data=refresh_data, headers=refresh_headers, timeout=10).json()
                
                if "access_token" in refresh_res:
                    # Cập nhật cặp token mới vào bộ nhớ trạng thái hệ thống
                    st.session_state.ZALO_ACCESS_TOKEN = refresh_res["access_token"]
                    st.session_state.ZALO_REFRESH_TOKEN = refresh_res["refresh_token"]
                    
                    # Cập nhật lại header và thực hiện lệnh gửi lại ngay lập tức
                    headers["access_token"] = st.session_state.ZALO_ACCESS_TOKEN
                    requests.post(url, json=payload, headers=headers, timeout=10)
                    st.success("🔄 Đã tự động gia hạn Token Zalo thành công!")
                    break
                else:
                    st.error(f"❌ Gia hạn Token Zalo thất bại: {refresh_res.get('error_description')}")
                    break
            else:
                st.error(f"❌ Zalo trả về mã lỗi: {result.get('message')} (Mã: {result.get('error')})")
                break
                
        except requests.exceptions.Timeout:
            # Xử lý nếu lần đầu tiên gọi bị nghẽn mạng (Timeout)
            if attempt == 0:
                print("⏳ Đường truyền nghẽn (Read timeout), đang tự động thử lại lần 2...")
                time.sleep(1) # Nghỉ 1 giây để đường truyền ổn định rồi lặp lại
                continue
            else:
                st.warning("⚠️ Kết nối tới Zalo quá chậm, hệ thống đã tự bỏ qua để tránh treo ứng dụng.")
        except Exception as e:
            st.error(f"❌ Lỗi kết nối hệ thống Zalo: {e}")
            break

# =====================================================================
# 2. LOGIC TOÁN HỌC VÀ ĐÁNH GIÁ TRẠNG THÁI VPD
# =====================================================================
def calculate_vpd(temp, humi):
    """
    Công thức toán học tính áp suất hơi bão hòa và độ hụt áp suất hơi (VPD)
    """
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
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
st.write("Dữ liệu cập nhật liên tục. Trạng thái bất thường (Báo động đỏ) sẽ lập tức gửi về Zalo Duy.")

# Hàm môphỏng lấy dữ liệu thời gian thực từ phần cứng IoT gửi về
def fetch_iot_garden_data():
    np.random.seed(int(time.time()))
    data = {
        "Trạm Vườn": ["Trạm 1 (Khu A)", "Trạm 2 (Khu B)", "Trạm 3 (Khu C)", "Trạm 4 (Khu D)", "Trạm 5 (Khu E)"],
        "Nhiệt độ (°C)": np.round(np.random.uniform(22.0, 35.0, 5), 1),
        "Độ ẩm (%)": np.round(np.random.uniform(40.0, 95.0, 5), 1)
    }
    return pd.DataFrame(data)

# Thực thi quét dữ liệu
df_garden = fetch_iot_garden_data()

# Tính toán chỉ số VPD tự động điền vào bảng dữ liệu
df_garden["VPD (kPa)"] = df_garden.apply(lambda row: round(calculate_vpd(row["Nhiệt độ (°C)"], row["Độ ẩm (%)"]), 2), axis=1)

# Thiết lập cấu trúc giao diện hiển thị 5 trạm dạng hàng ngang trực quan
cols = st.columns(5)
zalo_alert_messages = []

for idx, row in df_garden.iterrows():
    status_text, style = evaluate_station_status(row["Nhiệt độ (°C)"], row["Độ ẩm (%)"], row["VPD (kPa)"])
    
    with cols[idx]:
        st.markdown(f"### {row['Trạm Vườn']}")
        st.metric(label="🌡️ Nhiệt độ", value=f"{row['Nhiệt độ (°C)']} °C")
        st.metric(label="💧 Độ ẩm", value=f"{row['Độ ẩm (%)']} %")
        st.metric(label="📊 Chỉ số VPD", value=f"{row['VPD (kPa)']} kPa")
        
        # Đổ màu thông báo tương ứng lên giao diện Web Streamlit
        if style == "success":
            st.success(status_text)
        elif style == "warning":
            st.warning(status_text)
        elif style == "danger":
            st.error(status_text)
            # Chỉ gom các trạm bị lỗi "BÁO ĐỘNG" nguy hiểm để gửi tin nhắn
            zalo_alert_messages.append(f"- {row['Trạm Vườn']}: T={row['Nhiệt độ (°C)']}°C, H={row['Độ ẩm (%)']}%, VPD={row['VPD (kPa)']}kPa -> {status_text}")
        else:
            st.info(status_text)

st.markdown("---")
st.markdown("### 📋 Bảng Dữ Liệu Tổng Hợp 5 Trạm Vườn")
st.dataframe(df_garden, use_container_width=True)

# =====================================================================
# 4. KÍCH HOẠT GỬI TIN QUA ZALO KHI PHÁT HIỆN BẤT THƯỜNG
# =====================================================================
if zalo_alert_messages:
    # Gom tất cả các trạm lỗi vào 1 tin nhắn tổng hợp để tránh spam hạn mức tin Zalo cá nhân
    final_zalo_msg = "⚠️ HỆ THỐNG CẢNH BÁO VƯỜN THÔNG MINH (DUY TRẦN):\n" + "\n".join(zalo_alert_messages)
    
    # Kiểm tra chống gửi trùng lặp nội dung tin nhắn liên tiếp gây phiền nhiễu
    if "last_alert_content" not in st.session_state or st.session_state.last_alert_content != final_zalo_msg:
        send_zalo_bot_official(final_zalo_msg)
        st.session_state.last_alert_content = final_zalo_msg
else:
    st.info("✅ Hiện tại tất cả 5 trạm vườn đều đang hoạt động trong ngưỡng an toàn ổn định.")
