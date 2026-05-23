import streamlit as st
import random
import math
from datetime import datetime
import pandas as pd

# Cau hinh trang web Streamlit
st.set_page_config(page_title="He thong VPD dieu khien", page_icon="🌿", layout="centered")

st.title("He Thong Giam Sat va Tinh Toan VPD")

# --- CONG THUC TINH VPD ---
def calculate_vpd(temp, rh):
    vp_sat = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    vpd = vp_sat * (1.0 - (rh / 100.0))
    return vpd

# --- KHOI TAO BIEN TRONG SESSION STATE ---
if 'temp' not in st.session_state:
    st.session_state.temp = 31.5
if 'rh' not in st.session_state:
    st.session_state.rh = 56.5
if 'countdown' not in st.session_state:
    st.session_state.countdown = 30  
if 'last_updated' not in st.session_state:
    st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")
if 'stt_counter' not in st.session_state:
    st.session_state.stt_counter = 1

# Bien kiem tra trang thai chay (Mac dinh la dung)
if 'is_running' not in st.session_state:
    st.session_state.is_running = False

# Khoi tao danh sach lich su du lieu
if 'history' not in st.session_state:
    first_vpd = calculate_vpd(st.session_state.temp, st.session_state.rh)
    st.session_state.history = [{
        "STT": st.session_state.stt_counter,
        "Thoi gian": st.session_state.last_updated,
        "Nhiet do (degC)": st.session_state.temp,
        "Do am (%)": st.session_state.rh,
        "VPD (kPa)": round(first_vpd, 2)
    }]

# --- HAM RANDOM VA LUU LICH SU ---
def trigger_new_data():
    st.session_state.temp = round(random.uniform(15.0, 38.0), 1)
    st.session_state.rh = round(random.uniform(30.0, 95.0), 1)
    st.session_state.countdown = 30 
    st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")
    st.session_state.stt_counter += 1
    
    new_vpd = calculate_vpd(st.session_state.temp, st.session_state.rh)
    new_record = {
        "STT": st.session_state.stt_counter,
        "Thoi gian": st.session_state.last_updated,
        "Nhiệt độ (degC)": st.session_state.temp,
        "Do am (%)": st.session_state.rh,
        "VPD (kPa)": round(new_vpd, 2)
    }
    st.session_state.history.insert(0, new_record)

# --- KHU VUC DIEU KHIEN ---
st.subheader("Bang Dieu Khien")
col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("Bat dau chay tu dong", type="primary", disabled=st.session_state.is_running):
        st.session_state.is_running = True
        st.rerun()

with col_btn2:
    if st.button("Tam dung he thong", type="secondary", disabled=not st.session_state.is_running):
        st.session_state.is_running = False
        st.rerun()

st.write("---")

# --- DOAN CODE TU DONG QUET ---
run_interval = 1 if st.session_state.is_running else 999999

@st.fragment(run_every=run_interval)
def vpd_controlled_monitor():
    # 1. Xu ly dem nguoc
    if st.session_state.is_running:
        st.session_state.countdown -= 1
        if st.session_state.countdown < 0:
            trigger_new_data()
            
    # 2. Hien thi trang thai dong ho
    if st.session_state.is_running:
        st.success("He thong dang HOAT DONG tu dong")
        st.write(f"Tu dong doi so sau: **{st.session_state.countdown}** giay")
        st.progress(st.session_state.countdown / 30)
    else:
        st.error("He thong dang TAM DUNG (Bam Bat dau de chay)")
        st.write("Dang cho kich hoat...")
        st.progress(1.0)
        
    st.caption(f"Cap nhat gan nhat: {st.session_state.last_updated} - Lan thu: {st.session_state.stt_counter}")
    st.write("---")

    # 3. Hien thi so do hien tai
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Nhiet do hien tai", value=f"{st.session_state.temp} degC")
    with col2:
        st.metric(label="Do am hien tai", value=f"{st.session_state.rh} %")
        
    vpd_result = calculate_vpd(st.session_state.temp, st.session_state.rh)
    
    st.write("---")
    st.markdown("### Chi so VPD hien tai:")
    st.metric(label="Vapor Pressure Deficit", value=f"{vpd_result:.2f} kPa")
    
    # 4. Danh gia moi truong
    if vpd_result < 0.4:
        st.warning("VPD qua thap (Moi truong qua am): Cay kho thoat nuoc.")
    elif 0.4 <= vpd_result <= 0.8:
        st.info("VPD Thap: Phu hop giai doan nhan giong, kich re.")
    elif 0.8 < vpd_result <= 1.2:
        st.success("VPD Ly tuong: Moi truong hoan hao cho cay phat trien.")
    elif 1.2 < vpd_result <= 1.6:
        st.info("VPD Hoi cao: Phu hop giai doan ra hoa, tao qua.")
    else:
        st.error("VPD qua cao (Moi truong kho): Cay mat nuoc nhanh.")

    # Nut random nhanh
    if st.button("Random Thu Cong (1 lan)", type="secondary"):
        trigger_new_data()
        st.rerun()

    # --- 5. LICH SU DU LIEU ---
    st.write("---")
    st.markdown("### Lich Su Du Lieu Da Ghi Nhan")
    df_history = pd.DataFrame(st.session_state.history)
    st.dataframe(df_history, use_container_width=True, hide_index=True)
    
    # Nut xoa lich su
    if st.button("Xoa Lich Su"):
        st.session_state.stt_counter = 1
        st.session_state.history = [{
            "STT": st.session_state.stt_counter,
            "Thoi gian": st.session_state.last_updated,
            "Nhiet do (degC)": st.session_state.temp,
            "Do am (%)": st.session_state.rh,
            "VPD (kPa)": round(vpd_result, 2)
        }]
        st.rerun()

# Chay toan bo ung dung
vpd_controlled_monitor()
