from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from utils.asug import get_ai_suggestion
import os
import uuid # Untuk generate ID unik chat
from datetime import datetime # Untuk default title chat

load_dotenv()

app = Flask(__name__)
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

    # Tambahkan pesan ke chat yang aktif
    ai_response = get_ai_suggestion(user_message)
    session['chats'][current_chat_id]['messages'].append({'sender': 'user', 'message': user_message})
    session['chats'][current_chat_id]['messages'].append({'sender': 'ai', 'message': ai_response})
    
    # Logika untuk membuat judul otomatis oleh AI (dipindahkan dari app.py)
    current_chat_data = session['chats'][current_chat_id]
    # Judul dibuat setelah ada 1 pasang pertanyaan pengguna & jawaban AI (total 3 pesan: AI awal, User, AI)
    # Dan jika judul masih mengandung "Chat Baru"
    if "Chat Baru" in current_chat_data['title'] and len(current_chat_data['messages']) >= 3:
        try:
            user_first_q = current_chat_data['messages'][1]['message']
            context_for_title = f"Buatlah judul yang sangat singkat (maksimal 5 kata dan relevan) untuk percakapan yang diawali dengan pertanyaan: '{user_first_q}'"
            generated_title = get_ai_suggestion(context_for_title)
            # Bersihkan judul dari prefix atau newline yang mungkin dihasilkan AI
            generated_title = generated_title.replace("Judul:", "").replace("Title:", "").strip().split('\n')[0]
            if generated_title: # Pastikan judul tidak kosong
                session['chats'][current_chat_id]['title'] = generated_title[:50] # Batasi panjang judul
        except Exception as e:
            print(f"Error generating title with AI: {e}") # Log error, jangan sampai mengganggu chat utama

    session.modified = True
    return jsonify({'response': ai_response, 'new_title': session['chats'][current_chat_id]['title']})