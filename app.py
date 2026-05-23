import streamlit as pd
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import json
from datetime import datetime

# Cấu hình trang ứng dụng hiển thị rộng rãi, dễ nhìn
st.set_page_config(
    page_title="Hệ Thống Giám Sát VPD Thời Gian Thực",
    page_icon="📊",
    layout="wide"
)

# Tự động khởi tạo dữ liệu mô phỏng ban đầu trong Session State nếu chưa có
if "mqtt_df" not in st.session_state:
    now = datetime.now()
    # Tạo dữ liệu giả lập cho 5 trạm trong vòng vài phút trước để biểu đồ có sẵn đường vẽ
    init_data = []
    for i in range(5):  # 5 trạm từ STT 1 đến 5
        for mins in range(10, 0, -2):
            time_sub = now - pd.Timedelta(minutes=mins)
            init_data.append({
                "Thời gian": time_sub.strftime("%Y-%m-%d %H:%M:%S"),
                "STT": i + 1,
                "Nhiệt độ": round(np.random.uniform(22.0, 28.0), 1),
                "Độ ẩm": round(np.random.uniform(65.0, 85.0), 1)
            })
    st.session_state.mqtt_df = pd.DataFrame(init_data)

# =====================================================================
# HÀM TÍNH TOÁN CHỈ SỐ VPD (Vapor Pressure Deficit)
# =====================================================================
def calculate_vpd(temp, humidity):
    """
    Tính toán áp suất hơi bão hòa (SVP) và áp suất hơi thực tế (AVP)
    để suy ra độ hụt áp suất hơi (VPD) theo đơn vị kPa.
    """
    try:
        # Áp suất hơi bão hòa (SVP) ở nhiệt độ t (°C)
        svp = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
        # Áp suất hơi thực tế (AVP) dựa trên độ ẩm (%)
        avp = svp * (humidity / 100.0)
        # Độ hụt áp suất hơi (VPD)
        vpd = svp - avp
        return max(0.0, vpd)
    except:
        return 0.0

# =====================================================================
# GIAO DIỆN CHÍNH - TIÊU ĐỀ ỨNG DỤNG
# =====================================================================
st.title("📊 Hệ Thống Giám Sát Dữ Liệu & Quản Lý Ngưỡng VPD")
st.markdown("---")

# =====================================================================
# CẤU HÌNH HIỂN THỊ FULL CÂY TRỒNG VÀ CLICK CHỌN LỒNG NGƯỠNG VPD
# =====================================================================
st.subheader("⚙️ Cài Đặt Ngưỡng VPD Theo Loại Cây")
st.markdown("💡 *Click vào các ô vuông dưới đây để chọn loại cây trồng chung khu vực (Hệ thống tự lồng vùng tối ưu):*")

# Bảng cấu hình chuẩn vùng VPD cho các cây trồng phổ biến tại Đà Lạt
PLANT_PRESETS = {
    "🥒 Dưa leo": (0.70, 1.30),
    "🍓 Dâu tây": (0.40, 0.80),
    "🍅 Cà chua": (0.60, 1.20),
    "🫑 Ớt chuông": (0.50, 1.00),
    "🥬 Xà lách": (0.40, 0.85),
    "🌹 Hoa hồng": (0.80, 1.20)
}

# Chia lưới thành 3 cột để hiển thị các ô vuông song song cho đẹp mắt
cols = st.columns(3)
selected_bounds = []

# Duyệt qua toàn bộ danh sách cây và hiển thị trực tiếp ra màn hình dưới dạng Checkbox
for index, (plant_name, bounds) in enumerate(PLANT_PRESETS.items()):
    with cols[index % 3]:
        # Tạo ô vuông click chọn độc lập cho từng cây
        is_selected = st.checkbox(f"{plant_name} ({bounds[0]} - {bounds[1]} kPa)", key=f"chk_{index}")
        if is_selected:
            selected_bounds.append(bounds)

# Khối logic tự động tính toán khoảng lồng nhau khi click các ô vuông
default_low = 0.45
default_high = 1.70

if selected_bounds:
    # Thuật toán tìm vùng giao nhau (Overlap) lý tưởng: Cận dưới lớn nhất và Cận trên nhỏ nhất
    calculated_low = max(bound[0] for bound in selected_bounds)
    calculated_high = min(bound[1] for bound in selected_bounds)
    
    # Nếu vùng lồng nhau hợp lệ, áp dụng ngay
    if calculated_low < calculated_high:
        default_low = calculated_low
        default_high = calculated_high
    else:
        # Nếu các cây chọi nhau không có vùng chung, lấy khoảng rộng nhất bao quát cả hai để đảm bảo an toàn
        default_low = min(bound[0] for bound in selected_bounds)
        default_high = max(bound[1] for bound in selected_bounds)

# Hiển thị 2 thanh trượt điều chỉnh ngưỡng (Giá trị tự nhảy theo các ô vuông được click)
low_threshold = st.slider(
    "1. Ngưỡng VPD Thấp (Quá ẩm):", 
    min_value=0.1, max_value=1.5, 
    value=default_low, 
    step=0.05, format="%.2f kPa",
    key="slider_low_val"
)

high_threshold = st.slider(
    "2. Ngưỡng VPD Cao (Khô nóng):", 
    min_value=1.0, max_value=3.0, 
    value=default_high, 
    step=0.05, format="%.2f kPa",
    key="slider_high_val"
)

# Lưu giá trị vào session_state để các thành phần khác đồng bộ sử dụng
st.session_state.low_threshold = low_threshold
st.session_state.high_threshold = high_threshold

st.markdown("---")

# =====================================================================
# BIỂU ĐỒ TRỰC QUAN HÓA DỮ LIỆU (REAL-TIME CHARTS)
# =====================================================================
st.subheader("📈 Biểu Đồ Giám Sát Thời Gian Thực")

chart_df = st.session_state.mqtt_df.copy()

if not chart_df.empty:
    # Đồng bộ định dạng thời gian và sắp xếp thứ tự tăng dần
    chart_df['Thời gian'] = pd.to_datetime(chart_df['Thời gian'])
    chart_df = chart_df.sort_values('Thời gian')
    
    # Hàm chuẩn hóa dữ liệu từ các cảm biến phần cứng trước khi tính toán
    def apply_calc_vpd(row):
        t = pd.to_numeric(row['Nhiệt độ'])
        h = pd.to_numeric(row['Độ ẩm'])
        stt = str(row['STT'])
        if stt != "5" and t > 100: t /= 10.0
        if stt != "5" and h > 100: h /= 10.0
        return round(calculate_vpd(t, h), 3)

    # Tính toán cột chỉ số VPD cho toàn bộ bảng dữ liệu biểu đồ
    chart_df['VPD (kPa)'] = chart_df.apply(apply_calc_vpd, axis=1)
    
    # Ô chọn để bật/tắt chế độ lồng các đường trạm vào chung một hệ trục (Mặc định bật)
    overlay_mode = st.checkbox("🔄 Vẽ các đường Trạm lồng nhau trên cùng một hệ trục", value=True)
    chart_color = "STT" if overlay_mode else None

    # Phân chia giao diện quản lý biểu đồ thành 2 Tab mượt mà
    tab1, tab2 = st.tabs(["🌡️ Biểu đồ Nhiệt Độ", "💨 Biểu đồ Chỉ số VPD"])
    
    with tab1:
        fig_temp = px.line(
            chart_df, x="Thời gian", y="Nhiệt độ", color=chart_color, markers=True,
            title="Biến động Nhiệt độ hệ thống giữa các Trạm",
            labels={"Nhiệt độ": "Nhiệt độ (°C)", "STT": "Trạm"}
        )
        fig_temp.update_layout(
            xaxis_title="Thời gian", 
            yaxis_title="Nhiệt độ (°C)", 
            hovermode="x unified"
        )
        st.plotly_chart(fig_temp, use_container_width=True, key="chart_temp")

    with tab2:
        fig_vpd = px.line(
            chart_df, x="Thời gian", y="VPD (kPa)", color=chart_color, markers=True,
            title="Biến động Chỉ số VPD hệ thống giữa các Trạm",
            labels={"VPD (kPa)": "VPD (kPa)", "STT": "Trạm"}
        )
        # Thêm 2 đường nét đứt biểu thị vùng ranh giới an toàn động chạy theo thanh trượt slider phía trên
        fig_vpd.add_hline(y=low_threshold, line_dash="dash", line_color="blue", annotation_text="Ngưỡng quá ẩm")
        fig_vpd.add_hline(y=high_threshold, line_dash="dash", line_color="red", annotation_text="Ngưỡng khô nóng")
        
        fig_vpd.update_layout(
            xaxis_title="Thời gian", 
            yaxis_title="VPD (kPa)", 
            hovermode="x unified"
        )
        st.plotly_chart(fig_vpd, use_container_width=True, key="chart_vpd")
else:
    st.info("Đang chờ nhận dữ liệu từ các trạm cảm biến để vẽ đồ thị...")
