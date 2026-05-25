import altair as alt

def draw_vpd_chart(df, vpd_min, vpd_max):
    """Biểu đồ đường VPD kèm theo vùng an toàn (Lý tưởng) màu xanh"""
    base = alt.Chart(df).encode(
        x=alt.X('Hiển thị Giờ:N', sort=None, title='Mốc thời gian (10 phút/chu kỳ)')
    )
    
    # Vùng dải lý tưởng nền
    band = alt.Chart(df).mark_rect(opacity=0.15, color='#2ECC71').encode(
        y=alt.value(vpd_min),
        y2=alt.value(vpd_max)
    )
    
    # Đường đồ thị thực tế
    line = base.mark_line(point=True, color='#27AE60', strokeWidth=3).encode(
        y=alt.Y('VPD (kPa):Q', title='Áp suất thâm hụt (kPa)'),
        tooltip=['Hiển thị Giờ', 'Nhiệt độ (°C)', 'Độ ẩm (%)', 'VPD (kPa)', 'Trạng thái']
    )
    
    return (band + line).properties(height=320, title="Diễn biến chỉ số VPD thực tế đối chiếu dải lý tưởng")

def draw_temperature_chart(df):
    """Biểu đồ nhiệt độ"""
    return alt.Chart(df).mark_line(point=True, color='#E74C3C').encode(
        x=alt.X('Hiển thị Giờ:N', sort=None, title='Thời gian'),
        y=alt.Y('Nhiệt độ (°C):Q', title='Nhiệt độ (°C)'),
        tooltip=['Hiển thị Giờ', 'Nhiệt độ (°C)']
    ).properties(height=180)

def draw_humidity_chart(df):
    """Biểu đồ độ ẩm"""
    return alt.Chart(df).mark_line(point=True, color='#3498DB').encode(
        x=alt.X('Hiển thị Giờ:N', sort=None, title='Thời gian'),
        y=alt.Y('Độ ẩm (%):Q', title='Độ ẩm (%)'),
        tooltip=['Hiển thị Giờ', 'Độ ẩm (%)']
    ).properties(height=180)

def draw_combined_chart(df):
    """Không sử dụng hoặc để trống cho tính năng nâng cao"""
    return None
