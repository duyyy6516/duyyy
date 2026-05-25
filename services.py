import requests

def send_telegram_message(token, chat_id, message):
    """Gửi thông báo khẩn cấp qua Telegram Bot"""
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=3)
        return response.status_code == 200
    except:
        return False

def get_quick_solution(vpd, vpd_min, vpd_max):
    """Đưa ra giải pháp vận hành phần cứng tự động dựa trên thuật toán rẽ nhánh"""
    if vpd < vpd_min:
        return (
            "🚨 [QUÁ ẨM - NGUY CƠ BỆNH CAO]\n"
            "👉 Giải pháp: Tắt hệ thống tưới phun sương ngay lập tức.\n"
            "👉 Thiết bị: Bật quạt đối lưu không khí, mở rèm thông gió, bật đèn nhiệt sưởi (nếu có)."
        )
    elif vpd > vpd_max:
        return (
            "🚨 [QUÁ KHÔ - CÂY STRESS ĐÓNG KHÍ KHỔNG]\n"
            "👉 Giải pháp: Kích hoạt phun sương hạt mịn để tăng ẩm hạ nhiệt.\n"
            "👉 Thiết bị: Bật hệ thống tưới sàn, kéo rèm lưới che bớt nắng gắt."
        )
    else:
        return "✅ Môi trường đang Lý tưởng. Duy trì chế độ tự động thông gió nhẹ."
