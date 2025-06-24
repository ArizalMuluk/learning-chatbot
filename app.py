from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
from dotenv import load_dotenv
from utils.asug import get_ai_suggestion
import os
import uuid # Untuk generate ID unik chat
from datetime import datetime # Untuk default title chat
import json

load_dotenv()

# Get the directory of the current file (app.py or index.py)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Assuming 'templates' folder is one level up from the current file's directory
template_dir = os.path.join(current_dir, '..', 'templates')
app = Flask(__name__, template_folder=template_dir)
# Penting: Atur SECRET_KEY untuk menggunakan sesi Flask
# Ganti dengan kunci rahasia yang kuat dan unik di lingkungan produksi
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24)) # Lebih baik dari variabel lingkungan

def get_initial_ai_message():
    return "Halo! Saya adalah asisten belajarmu. Siap membantu dengan Bahasa Inggris, Matematika, atau Sains. Ada yang bisa saya bantu?"

def generate_chat_id():
    return str(uuid.uuid4())

def get_default_chat_title():
    return f"Chat Baru - {datetime.now().strftime('%H:%M %d/%m')}"

@app.route('/')
def index():
    if 'chats' not in session: # 'chats' akan menyimpan semua histori chat
        session['chats'] = {}

    if 'current_chat_id' not in session or session['current_chat_id'] not in session['chats']:
        # Jika tidak ada chat aktif atau ID tidak valid, buat chat baru
        new_chat_id = generate_chat_id()
        session['chats'][new_chat_id] = {
            'title': get_default_chat_title(),
            'messages': [{'sender': 'ai', 'message': get_initial_ai_message()}]
        }
        session['current_chat_id'] = new_chat_id
        session.modified = True

    current_chat_id = session['current_chat_id']
    current_chat_messages = session['chats'][current_chat_id]['messages']
    
    # Siapkan daftar judul chat untuk sidebar, urutkan agar yang terbaru (berdasarkan penambahan) di atas
    chat_titles = [{'id': chat_id, 'title': data['title']} for chat_id, data in session['chats'].items()]
    chat_titles.reverse() # Asumsi penambahan baru ada di akhir dict, jadi reverse untuk tampil terbaru

    return render_template('chat.html', 
                           chat_history=current_chat_messages, 
                           all_chat_titles=chat_titles,
                           current_chat_id=current_chat_id)

@app.route('/new_chat', methods=['POST']) # Gunakan POST untuk aksi yang mengubah state
def new_chat():
    new_chat_id = generate_chat_id()
    session['chats'][new_chat_id] = {
        'title': get_default_chat_title(), 
        'messages': [{'sender': 'ai', 'message': get_initial_ai_message()}]
    }
    session['current_chat_id'] = new_chat_id
    session.modified = True
    return redirect(url_for('index'))

@app.route('/load_chat/<chat_id>', methods=['GET'])
def load_chat(chat_id):
    if chat_id in session.get('chats', {}):
        session['current_chat_id'] = chat_id
        session.modified = True
    return redirect(url_for('index'))

@app.route('/delete_chat/<chat_id>', methods=['POST'])
def delete_chat(chat_id):
    if chat_id in session.get('chats', {}):
        del session['chats'][chat_id]
        if session.get('current_chat_id') == chat_id:
            # Jika chat yang dihapus adalah yang aktif, pilih chat lain atau biarkan index() membuat baru
            if session['chats']:
                session['current_chat_id'] = next(iter(session['chats'])) # Ambil ID chat pertama yang tersisa
            else:
                session.pop('current_chat_id', None) # Hapus current_chat_id jika tidak ada chat tersisa
        session.modified = True
    return redirect(url_for('index'))

@app.route('/send_message', methods=['POST'])
def send_message():
    # Perbaikan: Menangani kasus di mana request body bukan JSON
    data = request.get_json(silent=True)
    if not data or 'message' not in data:
        return jsonify({'error': 'Request tidak valid atau pesan tidak ada.'}), 400

    user_message = data.get('message')
    current_chat_id = session.get('current_chat_id')

    if not user_message:
        return jsonify({'error': 'Pesan kosong!'}), 400
    if not current_chat_id or current_chat_id not in session.get('chats', {}):
        return jsonify({'error': 'Sesi chat tidak valid atau tidak ditemukan.'}), 400

    def generate_stream():
        try:
            # Panggil fungsi AI dalam mode streaming
            for line in get_ai_suggestion(user_message, stream=True):
                # Teruskan setiap potongan data ke klien
                yield line
        except Exception as e:
            print(f"Error during stream generation: {e}")
            error_payload = {"error": "Terjadi kesalahan internal saat memproses respons AI."}
            yield f"data: {json.dumps(error_payload)}\n\n"

    return Response(generate_stream(), mimetype='text/event-stream')

@app.route('/save_chat', methods=['POST'])
def save_chat():
    data = request.get_json()
    user_message = data.get('user_message')
    ai_message = data.get('ai_message')
    current_chat_id = session.get('current_chat_id')

    if not all([user_message, ai_message, current_chat_id]) or current_chat_id not in session['chats']:
        return jsonify({'error': 'Data tidak lengkap atau sesi tidak valid.'}), 400

    # Simpan pesan pengguna dan AI ke sesi
    chat_messages = session['chats'][current_chat_id]['messages']
    # Hindari duplikasi jika frontend mengirim pesan pengguna lagi
    if not chat_messages or chat_messages[-1]['message'] != user_message:
        chat_messages.append({'sender': 'user', 'message': user_message})
    chat_messages.append({'sender': 'ai', 'message': ai_message})

    # Logika pembuatan judul otomatis
    new_title = None
    current_chat_data = session['chats'][current_chat_id]
    if "Chat Baru" in current_chat_data['title'] and len(current_chat_data['messages']) >= 2: # Cukup 1 pasang pesan
        try:
            user_first_q = next((msg['message'] for msg in current_chat_data['messages'] if msg['sender'] == 'user'), None)
            if user_first_q:
                context_for_title = f"Buatlah judul yang sangat singkat (maksimal 5 kata dan relevan) untuk percakapan yang diawali dengan pertanyaan: '{user_first_q}'"
                generated_title_raw = get_ai_suggestion(context_for_title, stream=False)
                
                if generated_title_raw and not generated_title_raw.startswith("Maaf,"):
                    generated_title = generated_title_raw.replace("Judul:", "").replace("Title:", "").strip().split('\n')[0]
                    if generated_title:
                        new_title = generated_title.strip('"').strip("'")[:50]
                        session['chats'][current_chat_id]['title'] = new_title
        except Exception as e:
            print(f"Error generating title with AI: {e}")
    
    session.modified = True

    return jsonify({
        'status': 'success', 
        'new_title': new_title or session['chats'][current_chat_id]['title']
    })

if __name__ == '__main__':
    app.run(debug=True)