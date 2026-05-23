# --- CONTAINER 6: BIỂU ĐỒ XU HƯỚNG TƯƠNG TÁC (ĐÃ SỬA LỖI TRỤC Y VÀ HIỂN THỊ) ---
    if len(st.session_state.history) > 0:
        st.write("")
        with st.container(border=True):
            st.markdown("<p style='color: gray; font-size: 14px; margin-bottom: 2px;'>📈 BIỂU ĐỒ XU HƯỚNG ĐỒNG BỘ CHU KỲ TRONG NGÀY</p>", unsafe_allow_html=True)
            st.caption("💡 *Mẹo:* Rê chuột vào các điểm nút trên đường vẽ để xem thông số chi tiết mốc giờ đó.")
            
            # Đảo ngược lịch sử để vẽ biểu đồ theo thứ tự thời gian tăng dần từ trái qua phải
            df_chart = pd.DataFrame(st.session_state.history).iloc[::-1].copy()
            
            tab_temp, tab_rh, tab_vpd = st.tabs(["🌡️ Biểu đồ Nhiệt độ", "💧 Biểu đồ Độ ẩm", "🎯 Biểu đồ chỉ số VPD"])
            
            with tab_temp:
                chart_temp = alt.Chart(df_chart).mark_line(color="#FF4B4B", point=True).encode(
                    x=alt.X('Hiển thị Giờ:O', axis=alt.Axis(title="Mốc thời gian", labelAngle=0)), 
                    y=alt.Y('Nhiệt độ (°C):Q', scale=alt.Scale(zero=False), axis=alt.Axis(title="Nhiệt độ (°C)")),
                    tooltip=['Ngày', 'Hiển thị Giờ', 'Nhiệt độ (°C)']
                ).properties(height=260)
                st.altair_chart(chart_temp, use_container_width=True)
                
            with tab_rh:
                chart_rh = alt.Chart(df_chart).mark_line(color="#0068C9", point=True).encode(
                    x=alt.X('Hiển thị Giờ:O', axis=alt.Axis(title="Mốc thời gian", labelAngle=0)),
                    y=alt.Y('Độ ẩm (%):Q', scale=alt.Scale(zero=False), axis=alt.Axis(title="Độ ẩm (%)")),
                    tooltip=['Ngày', 'Hiển thị Giờ', 'Độ ẩm (%)']
                ).properties(height=260)
                st.altair_chart(chart_rh, use_container_width=True)
                
            with tab_vpd:
                st.caption(f"ℹ️ Vùng màu an toàn theo [{plant_option}]: 🟦 Quá ẩm (< {vpd_min} kPa) | 🟥 Quá khô (> {vpd_max} kPa)")
                
                # Tạo lớp dữ liệu nền ảo và buộc trục Y của lớp nền không được hiển thị tiêu đề gây đè chữ
                bg_data = pd.DataFrame([{'start_blue': 0.0, 'end_blue': vpd_min, 'start_red': vpd_max, 'end_red': 3.0}])
                
                rect_blue = alt.Chart(bg_data).mark_rect(color='#0068C9', opacity=0.12).encode(
                    y=alt.Y('start_blue:Q', axis=None), 
                    y2=alt.Y2('end_blue:Q')
                )
                
                rect_red = alt.Chart(bg_data).mark_rect(color='#FF4B4B', opacity=0.12).encode(
                    y=alt.Y('start_red:Q', axis=None), 
                    y2=alt.Y2('end_red:Q')
                )
                
                # Đường vẽ đồ thị VPD chính sử dụng cột chuỗi giờ dễ đọc
                line_vpd = alt.Chart(df_chart).mark_line(color="#2E7D32", point=True).encode(
                    x=alt.X('Hiển thị Giờ:O', axis=alt.Axis(title="Mốc thời gian", labelAngle=0)),
                    y=alt.Y('VPD (kPa):Q', scale=alt.Scale(domain=[0, 3.0]), axis=alt.Axis(title="Chỉ số VPD (kPa)")),
                    tooltip=['Ngày', 'Hiển thị Giờ', 'VPD (kPa)', 'Trạng thái']
                )
                
                # Gom các lớp lại thành một biểu đồ thống nhất
                chart_vpd = (rect_blue + rect_red + line_vpd).properties(height=260)
                st.altair_chart(chart_vpd, use_container_width=True)
