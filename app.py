from datetime import timedelta

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
                if previous_ldr < 1000 and current_ldr >= 1000:
                    obat_count += 1
            previous_ldr = current_ldr

            # Tambahkan jumlah obat dan waktu yang disesuaikan (ditambah 7 jam)
            timestamp = record.get('timestamp')
            if timestamp:
                adjusted_timestamp = pd.to_datetime(timestamp) + timedelta(hours=7)
                changes['timestamp'] = adjusted_timestamp
            else:
                changes['timestamp'] = None

            changes['jumlah_obat'] = obat_count
            filtered_changes.append(changes)

        return pd.DataFrame(filtered_changes)
    except Exception as e:
        st.error(f"Gagal mengambil riwayat sensor: {str(e)}")
        return pd.DataFrame()
