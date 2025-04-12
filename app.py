import streamlit as st
import google.generativeai as genai

# ===========================
# KONFIGURASI AWAL
# ===========================
api_key = st.secrets["GEMINI_API"]
# Konfigurasi API
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

# Inisialisasi Session State
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

# ===========================
# FUNGSI UTAMA
# ===========================
def generate_medical_questions(history):
    """Generate questions using Gemini"""
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

def generate_recommendations():
    """Generate personalized recommendations"""
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

# ===========================
# HALAMAN APLIKASI
# ===========================
def main_page():
    """Halaman Utama"""
    st.title("🩺 Aplikasi Pemeriksaan Kesehatan")
    st.header("Apakah kamu merasa sakit hari ini?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya", help="Klik jika merasa tidak sehat", type="primary"):
            st.session_state.page = 'medical_history'
            st.rerun()
    with col2:
        if st.button("Tidak", help="Klik jika merasa sehat"):
            st.success("""
                       🎉 Bagus! Tetap jaga kesehatan dan perhatikan kondisi tubuh Anda.\n\n 
                       🥗 Tetap patuhi pola hidup sehat!
                       """)
            st.success("Jika ada gejala yang muncul, silakan kembali ke aplikasi ini.")

def medical_history_page():
    """Halaman Riwayat Medis"""
    st.title("📋 Riwayat Medis")
    
    with st.form("medical_form"):
        st.write("Mohon isi informasi berikut!")
        history = st.text_area(
            "Riwayat penyakit/kondisi medis yang pernah dimiliki :",
            height=150,
            key="medical_history"
        )
        
        if st.form_submit_button("Lanjutkan"):
            if history.strip():
                questions = generate_medical_questions(history)
                if questions:
                    st.session_state.generated_questions = questions
                    st.session_state.page = 'questioning'
                    st.session_state.current_question = 0
                    st.session_state.answers = []
                    st.rerun()
                else:
                    st.error("Gagal membuat pertanyaan. Silakan coba lagi.")
            else:
                st.warning("Mohon isi riwayat medis Anda terlebih dahulu")

def questioning_page():
    """Halaman Pertanyaan Gejala"""
    st.title("🔍 Pemeriksaan Gejala")
    
    if st.session_state.current_question < len(st.session_state.generated_questions):
        current_q = st.session_state.generated_questions[st.session_state.current_question]
        
        # Header Progress
        st.subheader(f"Pertanyaan {st.session_state.current_question + 1}/{len(st.session_state.generated_questions)}")
        st.progress((st.session_state.current_question + 1)/len(st.session_state.generated_questions))
        
        # Pertanyaan
        st.markdown(f"**{current_q.replace('-', '•')}**")
        
        # Tombol Jawaban
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Ya ✅", key=f"yes_{st.session_state.current_question}"):
                st.session_state.answers.append(True)
                st.session_state.current_question += 1
                st.rerun()
        with col2:
            if st.button("Tidak ❌", key=f"no_{st.session_state.current_question}"):
                st.session_state.answers.append(False)
                st.session_state.current_question += 1
                st.rerun()
    else:
        st.session_state.page = 'results'
        st.rerun()

def results_page():
    """Halaman Hasil Akhir"""
    st.title("📝 Hasil Analisis")
    
    # Generate Rekomendasi
    with st.spinner("🔄 Membuat analisis khusus untuk Anda..."):
        recommendations = generate_recommendations()
    
    # Tampilkan Hasil
    st.subheader("📊 Ringkasan Jawaban")
    st.write(f"Total gejala yang dialami: {sum(st.session_state.answers)} dari {len(st.session_state.answers)}")
    
    st.subheader("💡 Rekomendasi Medis")
    if recommendations:
        st.markdown(recommendations)
    else:
        st.warning("""
        **Rekomendasi Umum:**
        - Konsultasikan ke dokter umum terdekat
        - Pantau perkembangan gejala
        - Istirahat yang cukup
        - Hindari aktivitas berat
        """)
    
    # Tombol Reset
    st.divider()
    if st.button("🔄 Mulai Pemeriksaan Baru"):
        st.session_state.page = 'main'
        st.rerun()

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

# ===========================
# FOOTER
# ===========================
st.divider()
st.caption("⚠️ Aplikasi ini bukan pengganti diagnosis medis profesional. Selalu konsultasikan dengan tenaga kesehatan terkait kondisi medis Anda.")