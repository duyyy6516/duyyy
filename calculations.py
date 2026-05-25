import numpy as np

def calculate_vpd(temp, rh):
    """Tính chỉ số Áp suất thâm hụt hơi (VPD) - Đơn vị: kPa"""
    # Áp suất hơi bão hòa (SVP)
    svp = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    # Áp suất hơi thực tế (AVP)
    avp = svp * (rh / 100.0)
    # Thâm hụt áp suất hơi (VPD)
    vpd = svp - avp
    return round(vpd, 2)

def get_weather_by_time(dt):
    """Mô phỏng thời tiết Đà Lạt thay đổi tự nhiên theo giờ trong ngày"""
    hour = dt.hour
    minute = dt.minute
    time_frac = hour + minute / 60.0
    
    # Giờ lạnh nhất là 5:30 sáng, nóng nhất là 13:30 chiều
    temp_base = 16.0 + 8.0 * np.sin((time_frac - 7.5) * np.pi / 12.0)
    # Độ ẩm nghịch biến với nhiệt độ
    rh_base = 75.0 - 25.0 * np.sin((time_frac - 7.5) * np.pi / 12.0)
    
    # Thêm một chút nhiễu nhẹ tự nhiên (noise)
    np.random.seed(hour * 60 + minute)
    temp_noise = np.random.uniform(-0.4, 0.4)
    rh_noise = np.random.uniform(-1.5, 1.5)
    
    final_temp = round(temp_base + temp_noise, 1)
    final_rh = round(min(max(rh_base + rh_noise, 30.0), 100.0), 1)
    
    return final_temp, final_rh
