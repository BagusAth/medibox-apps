import streamlit as st
import google.generativeai as genai
from pymongo import MongoClient
from bson.json_util import dumps
import certifi
import pandas as pd
from datetime import datetime
import pytz

# ===========================
# KONFIGURASI AWAL
# ===========================
# API Key Gemini
api_key = st.secrets["GEMINI_API"]
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

# MongoDB Config
MONGO_URI = "mongodb+srv://bramantyo989:jkGjM7paFoethotj@cluster0.zgafu.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["SentinelSIC"]
collection = db["SensorSentinel"]

# Fungsi untuk mendapatkan timestamp lokal
def get_local_timestamp():
    # Ubah sesuai zona waktu lokal yang diinginkan, misal Asia/Jakarta
    local_tz = pytz.timezone("Asia/Jakarta")
    timestamp = datetime.now(local_tz)
    # Format timestamp sebagai string (bisa juga dikembalikan sebagai objek datetime jika perlu)
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

# ===========================
# PENGATURAN SESSION STATE
# ===========================
if 'page' not in st.session_state:
    st.session_state.page = 'main'
if 'medical_history' not in st.session_state:
    st.session_state.medical_history = ''
if 'generated_questions' not in st.session_state:
    st.session_state.generated_questions = []
if 'answers' not in st.session_state:
    st.session_state.answers = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'sensor_history' not in st.session_state:
    st.session_state.sensor_history = None
if 'reset_obat_count' not in st.session_state:
    st.session_state.reset_obat_count = False

# ===========================
# FUNGSI PENDUKUNG
# ===========================
def generate_medical_questions(history):
    prompt = f"""
    Anda adalah dokter profesional. Buat 3-5 pertanyaan spesifik tentang gejala 
    yang mungkin terkait dengan riwayat penyakit berikut:
    
    Riwayat Pasien: {history}
    
    Format output:
    - Apakah Anda mengalami [gejala spesifik]?
    - Apakah Anda merasa [gejala spesifik]?
    
    Hanya berikan list pertanyaan tanpa penjelasan tambahan.
    """
    try:
        response = model.generate_content(prompt)
        questions = response.text.split('\n')
        return [q.strip() for q in questions if q.strip() and q.startswith('-')]
    except Exception as e:
        st.error(f"Gagal membuat pertanyaan: {str(e)}")
        return []

def get_sensor_data():
    try:
        latest = list(collection.find().sort("timestamp", -1).limit(1))
        return latest[0] if latest else None
    except Exception as e:
        st.error(f"Gagal mengambil data dari MongoDB: {str(e)}")
        return None

def get_sensor_history(limit=50):
    try:
        # Ambil riwayat data sensor terbaru dari MongoDB
        records = list(collection.find().sort("timestamp", -1).limit(limit))
        # Urutkan dari yang paling lama ke terbaru
        records.reverse()  

        filtered_changes = []
        last = {}
        obat_count = 0  # Inisialisasi counter untuk jumlah obat

        previous_ldr = None  # Nilai ldr sebelumnya

        # Iterasi setiap record dan filter perubahan sensor
        for record in records:
            changes = {}
            for key in ['temperature', 'humidity', 'ldr_value']:
                current_val = record.get(key)
                changes[key] = current_val
                last[key] = current_val

            # Logika untuk menghitung penambahan obat
            current_ldr = record.get('ldr_value')
            if previous_ldr is not None:
                # Jika sebelumnya ldr_value dibawah 1000 dan sekarang mencapai atau di atas 1000,
                # maka naikkan counter obat
                if previous_ldr < 1000 and current_ldr >= 1000:
                    obat_count += 1
            # Simpan nilai ldr_value sekarang sebagai previous_ldr untuk iterasi selanjutnya
            previous_ldr = current_ldr

            # Tambahkan jumlah obat yang sudah diambil ke dalam record
            changes['jumlah_obat'] = obat_count

            # Pastikan memasukkan timestamp
            changes['timestamp'] = record.get('timestamp')
            filtered_changes.append(changes)

        # Buat DataFrame dari record yang telah difilter
        return pd.DataFrame(filtered_changes)
    except Exception as e:
        st.error(f"Gagal mengambil riwayat sensor: {str(e)}")
        return pd.DataFrame()

def generate_recommendations():
    try:
        history = st.session_state.medical_history or "Tidak ada riwayat"
        symptoms = "\n".join([
            f"{q} - {'Ya' if a else 'Tidak'}"
            for q, a in zip(st.session_state.generated_questions, st.session_state.answers)
        ])
        
        prompt = f"""
        Analisis riwayat medis dan gejala berikut:
        
        1. Riwayat Medis: {history}
        2. Gejala:
        {symptoms}
        
        Berikan rekomendasi dalam Bahasa Indonesia dengan format:
        - Analisis kondisi
        - Tindakan medis yang diperlukan
        - Langkah pencegahan
        - Rekomendasi dokter spesialis (jika perlu)
        - Tips perawatan mandiri
        
        Gunakan format markdown dengan poin-point jelas.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating recommendations: {str(e)}")
        return None

# Contoh fungsi untuk menyimpan data sensor dengan timestamp lokal ke MongoDB
def insert_sensor_data(temperature, humidity, ldr_value):
    sensor_data = {
        "temperature": temperature,
        "humidity": humidity,
        "ldr_value": ldr_value,
        "timestamp": get_local_timestamp()  # Menggunakan timestamp lokal
    }
    try:
        collection.insert_one(sensor_data)
    except Exception as e:
        st.error(f"Gagal menyimpan data sensor: {str(e)}")

# ===========================
# HALAMAN APLIKASI
# ===========================
def main_page():
    st.title("🩺 Aplikasi Pemeriksaan Kesehatan")
    
    st.header("Apakah kamu merasa sakit hari ini?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya", type="primary"):
            st.session_state.page = 'medical_history'
            st.experimental_rerun()
    with col2:
        if st.button("Tidak"):
            st.success("🎉 Bagus! Tetap jaga kesehatan...")

    st.divider()
    st.subheader("📚 Riwayat Perubahan Sensor")
    # Tombol Refresh Manual untuk data sensor historis
    if st.button("🔃 Refresh Riwayat Sensor"):
        new_history = get_sensor_history()
        if not new_history.empty:
            st.session_state.sensor_history = new_history
        else:
            latest_data = get_sensor_data()
            if latest_data and st.session_state.sensor_history is not None and not st.session_state.sensor_history.empty:
                st.session_state.sensor_history.loc[st.session_state.sensor_history.index[-1], 'temperature'] = latest_data.get('temperature')
                st.session_state.sensor_history.loc[st.session_state.sensor_history.index[-1], 'humidity'] = latest_data.get('humidity')

    if st.session_state.sensor_history is None or st.session_state.sensor_history.empty:
        st.session_state.sensor_history = get_sensor_history()

    df = st.session_state.sensor_history
    st.dataframe(df.sort_values(by="timestamp", ascending=False), use_container_width=True)

def medical_history_page():
    st.title("📋 Riwayat Medis")
    
    with st.form("medical_form"):
        history = st.text_area("Riwayat penyakit/kondisi medis yang pernah dimiliki :", height=150, key="medical_history")
        if st.form_submit_button("Lanjutkan"):
            if history.strip():
                questions = generate_medical_questions(history)
                if questions:
                    st.session_state.generated_questions = questions
                    st.session_state.page = 'questioning'
                    st.session_state.current_question = 0
                    st.session_state.answers = []
                    st.experimental_rerun()
                else:
                    st.error("Gagal membuat pertanyaan. Silakan coba lagi.")
            else:
                st.warning("Mohon isi riwayat medis Anda terlebih dahulu")

def questioning_page():
    st.title("🔍 Pemeriksaan Gejala")

    if st.session_state.current_question < len(st.session_state.generated_questions):
        current_q = st.session_state.generated_questions[st.session_state.current_question]

        st.subheader(f"Pertanyaan {st.session_state.current_question + 1}/{len(st.session_state.generated_questions)}")
        st.progress((st.session_state.current_question + 1) / len(st.session_state.generated_questions))
        st.markdown(f"**{current_q.replace('-', '•')}**")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Ya ✅", key=f"yes_{st.session_state.current_question}"):
                st.session_state.answers.append(True)
                st.session_state.current_question += 1
                st.experimental_rerun()
        with col2:
            if st.button("Tidak ❌", key=f"no_{st.session_state.current_question}"):
                st.session_state.answers.append(False)
                st.session_state.current_question += 1
                st.experimental_rerun()
    else:
        st.session_state.page = 'results'
        st.experimental_rerun()

def results_page():
    st.title("📝 Hasil Analisis")
    with st.spinner("🔄 Membuat analisis khusus untuk Anda..."):
        recommendations = generate_recommendations()

    st.subheader("📊 Ringkasan Jawaban")
    st.write(f"Total gejala yang dialami: {sum(st.session_state.answers)} dari {len(st.session_state.answers)}")

    st.subheader("💡 Rekomendasi Medis")
    if recommendations:
        st.markdown(recommendations)
    else:
        st.warning(
            """
            **Rekomendasi Umum:**
            - Konsultasikan ke dokter umum terdekat
            - Pantau perkembangan gejala
            - Istirahat yang cukup
            - Hindari aktivitas berat
            """
        )

    st.divider()
    if st.button("🔄 Mulai Pemeriksaan Baru"):
        st.session_state.page = 'main'
        st.experimental_rerun()

# Jika ada halaman sensor terpisah (jika diperlukan)
def sensor_page():
    st.title("📊 Data Sensor")
    # Implementasi halaman sensor jika diperlukan
    st.write("Halaman ini untuk data sensor secara khusus.")

# ===========================
# ROUTING HALAMAN
# ===========================
if st.session_state.page == 'main':
    main_page()
elif st.session_state.page == 'medical_history':
    medical_history_page()
elif st.session_state.page == 'questioning':
    questioning_page()
elif st.session_state.page == 'results':
    results_page()
elif st.session_state.page == 'sensor':
    sensor_page()

# ===========================
# FOOTER
# ===========================
st.divider()
st.caption("⚠️ Aplikasi ini bukan pengganti diagnosis medis profesional. Selalu konsultasikan dengan tenaga kesehatan terkait kondisi medis Anda.")
