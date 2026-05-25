import pandas as pd
import numpy as np

def get_biological_block(hour):
    """Phân chia buổi sinh học dựa trên đồng hồ sinh học của cây trồng"""
    if 5 <= hour < 10: return "🌅 Sáng (05h - 10h)"
    elif 10 <= hour < 15: return "☀️ Trưa (10h - 15h)"
    elif 15 <= hour < 19: return "🌇 Chiều (15h - 19h)"
    elif 19 <= hour < 23: return "🌌 Tối (19h - 23h)"
    else: return "🌙 Khuya (23h - 05h)"

def calculate_dew_point(temp, rh):
    """Tính điểm đọng sương (Dew Point) bằng công thức Magnus-Tetens"""
    a = 17.27
    b = 237.7
    alpha = ((a * temp) / (b + temp)) + np.log(rh / 100.0)
    return round((b * alpha) / (a - alpha), 2)

def predict_vpd_trend_v3(history_data, current_hour, vpd_min, vpd_max):
    """Dự báo xu hướng toán học dựa trên dải VPD cố định (Phiên bản v3)"""
    if not history_data or len(history_data) < 3:
        return "📊 Hệ thống đang tích lũy thêm chu kỳ dữ liệu...", "normal"
    try:
        v1 = float(history_data[0]["VPD (kPa)"])
        v2 = float(history_data[1]["VPD (kPa)"])
        v3 = float(history_data[2]["VPD (kPa)"])
        
        diff_1 = v1 - v2
        diff_2 = v2 - v3
        
        if abs(diff_1) < 0.005 and abs(diff_2) < 0.005:
            if v1 < vpd_min: return "🟦 CẢNH BÁO: Hiện trạng quá ẩm đang bị kẹt đứng im lâu. Cần bật quạt đối lưu lập tức.", "danger_blue"
            elif v1 > vpd_max: return "🟥 CẢNH BÁO: Hiện trạng khô nóng đang đứng im kéo dài. Cần kích hoạt hệ thống phun sương.", "danger_red"
            else: return "🟩 Xu hướng: Chỉ số VPD đang duy trì đi ngang rất ổn định trong dải lý tưởng.", "normal"
            
        slope = (diff_1 + diff_2) / 2.0
        
        if v1 > vpd_max and slope > 0.02: 
            return f"🚨 [CẢNH BÁO SỚM] Chỉ số đang vượt ngưỡng max {vpd_max} kPa và đang tiếp tục tăng khô gắt thêm!", "danger_red"
        if v1 < vpd_min and slope < -0.02: 
            return f"🚨 [CẢNH BÁO SỚM] Chỉ số đang tụt dưới ngưỡng min {vpd_min} kPa và đang có xu hướng ẩm ướt thêm!", "danger_blue"
            
        if slope > 0.04: return "📈 Xu hướng: Chỉ số VPD đang tăng nhanh (Khô dần).", "normal"
        elif slope < -0.04: return "📉 Xu hướng: Chỉ số VPD đang sụt giảm nhanh (Ẩm lên).", "normal"
        else: return "🔄 Xu hướng: Biến động biên độ nhỏ, nằm trong tầm kiểm soát sinh học.", "normal"
    except:
        return f"🔄 Chỉ số xu hướng đang được chuẩn hóa toán học...", "normal"

def calculate_plant_stress_hours(df_data, vpd_min, vpd_max, mode_filter):
    """Tính toán giờ Stress Khô / Ẩm tích lũy đối chiếu theo ngưỡng cố định"""
    if df_data.empty or "VPD (kPa)" not in df_data.columns:
        return {"dry_hours": 0.0, "wet_hours": 0.0, "fungus_risk": 0}
    
    if "1 Ngày gần nhất" in mode_filter or "10 phút" in mode_filter: 
        minutes_per_point = 10
    elif "1 Tuần gần nhất" in mode_filter or "1 Tháng gần nhất" in mode_filter: 
        minutes_per_point = 1440
    elif "Toàn bộ dữ liệu gốc" in mode_filter:
        if len(df_data) > 1 and "datetime_internal" in df_data.columns:
            try:
                time_diffs = pd.Series(df_data["datetime_internal"]).diff().dropna()
                minutes_per_point = time_diffs.dt.total_seconds().median() / 60.0
            except: minutes_per_point = 10
        else: minutes_per_point = 10
    else:
        minutes_per_point = 10

    dry_points = 0
    wet_points = 0
    fungus_points = 0

    for idx, row in df_data.iterrows():
        vpd_val = row["VPD (kPa)"]
        temp_val = row["Nhiệt độ (°C)"]
        
        if vpd_val > vpd_max:
            dry_points += 1
        elif vpd_val < vpd_min:
            wet_points += 1
            if 16.0 <= temp_val <= 25.0:
                fungus_points += 1
                
    dry_hours = round((dry_points * minutes_per_point) / 60.0, 1)
    wet_hours = round((wet_points * minutes_per_point) / 60.0, 1)
    fungus_hours = (fungus_points * minutes_per_point) / 60.0
    fungus_risk_pct = min(int((fungus_hours / 6.0) * 100), 100)
    
    return {
        "dry_hours": dry_hours,
        "wet_hours": wet_hours,
        "fungus_risk": fungus_risk_pct
    }

def analyze_day_by_blocks_rt(history_list, vpd_min, vpd_max, target_day_str):
    """Phân tích báo cáo chu kỳ buổi đối chiếu trực tiếp với ngưỡng cố định ban đầu"""
    if not history_list: return pd.DataFrame()
    df = pd.DataFrame(history_list)
    df_filtered = df[df["Ngày"] == target_day_str].copy()
    if df_filtered.empty: return pd.DataFrame()
    
    df_filtered["Buổi"] = df_filtered["datetime_internal"].dt.hour.apply(get_biological_block)
    summary = df_filtered.groupby("Buổi").agg({"Nhiệt độ (°C)": "mean", "Độ ẩm (%)": "mean", "VPD (kPa)": "mean"}).reindex([
        "🌅 Sáng (05h - 10h)", "☀️ Trưa (10h - 15h)", "🌇 Chiều (15h - 19h)", "🌌 Tối (19h - 23h)", "🌙 Khuya (23h - 05h)"
    ]).dropna()
    
    report_data = []
    for idx, row in summary.iterrows():
        avg_t = round(row["Nhiệt độ (°C)"], 1)
        avg_h = round(row["Độ ẩm (%)"], 1)
        avg_v = round(row["VPD (kPa)"], 2)
        
        if avg_v < vpd_min:
            status = f"⚠️ Quá ẩm (Mục tiêu: {vpd_min}-{vpd_max})"
            sol = "Bật quạt đối lưu khí mạnh, mở bớt màng thông gió rèm."
        elif avg_v > vpd_max:
            status = f"🚨 Quá khô (Mục tiêu: {vpd_min}-{vpd_max})"
            sol = "Kéo lưới cắt nắng sương, kích hoạt hệ thống phun mịn hạt."
        else:
            status = f"✅ Lý tưởng ({vpd_min}-{vpd_max})"
            sol = "Môi trường hoàn hảo cho buổi này. Duy trì hệ thống thông gió."
            
        report_data.append({
            "Khoảng Buổi": idx, "Nhiệt độ TB": f"{avg_t} °C", "Độ ẩm TB": f"{avg_h} %",
            "VPD Trung Bình": f"{avg_v} kPa", "Đánh giá sinh học": status, "Giải pháp kỹ thuật": sol
        })
    return pd.DataFrame(report_data)
