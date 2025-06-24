import os
import requests
import re
import json

def get_ai_suggestion(user_input, stream=False):
    """
    Fungsi ini akan berinteraksi dengan AI API untuk mendapatkan respons dalam Bahasa Indonesia
    dan memproteksi dari kata kasar serta unsur pelecehan seksual.
    Jika stream=True, fungsi ini akan menjadi generator.
    """

    # Daftar kata kasar dan pelecehan (bisa dikembangkan)
    banned_words = [
        "anjing", "bangsat", "kontol", "memek", "pepek", "ngentot", "tolol", "babi", "asu",
        "fuck", "bitch", "dick", "pussy", "sex", "seks", "bokep", "mesum", "sange", "bugil"
    ]
    pattern = re.compile(r'\b(' + '|'.join(banned_words) + r')\b', re.IGNORECASE)
    if pattern.search(user_input):
        if stream:
            yield f"data: {json.dumps({'error': 'Maaf, pesan Anda mengandung kata yang tidak pantas.'})}\n\n"
        else:
            return "Maaf, pesan Anda mengandung kata yang tidak pantas atau unsur pelecehan."

    API_GROQ = os.getenv('GROQ_AI')
    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    # Tambahkan sistem prompt agar AI selalu membalas dalam Bahasa Indonesia dan menolak permintaan tidak pantas
    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "Anda adalah asisten AI yang selalu membalas dalam Bahasa Indonesia. "
                    "Gunakan format Markdown untuk jawabanmu. Contohnya, gunakan `**teks tebal**` untuk huruf tebal, "
                    "`*teks miring*` untuk huruf miring, `-` untuk daftar list, dan `1.` untuk daftar bernomor. "
                    "Jika ada permintaan yang mengandung kata kasar, pelecehan, atau permintaan tidak pantas, "
                    "tolak dengan sopan."
                ),
            },
            {
                "role": "user",
                "content": user_input,
            }
        ], 
        "stream": stream,
        "model": "llama3-8b-8192"
    }

    headers = {
        "Authorization": f"Bearer {API_GROQ}",
        "Content-Type": "application/json"
    }

    try:
        # Gunakan stream=True untuk request agar koneksi tetap terbuka
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30, stream=stream)
        response.raise_for_status()

        if stream:
            # Menjadi generator, menghasilkan setiap baris dari stream
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        yield decoded_line + '\n\n' # Kirim event SSE lengkap
        else:
            # Perilaku non-streaming untuk fungsi seperti pembuatan judul
            ai_response = response.json()
            return ai_response['choices'][0]['message']['content']

    except requests.exceptions.RequestException as e:
        # Catch network-related errors (connection, timeout, HTTP status errors)
        error_message = f"Maaf, terjadi masalah koneksi ke AI: {type(e).__name__} - {e}"
        if stream:
            yield f"data: {json.dumps({'error': error_message})}\n\n"
        else:
            return error_message
    except (KeyError, json.JSONDecodeError) as e:
        # Catch errors if the AI response JSON is malformed or has an unexpected structure
        error_message = f"Maaf, format respons AI tidak sesuai: {type(e).__name__} - {e}"
        if stream: # This case is less likely for streaming, but good for consistency
            yield f"data: {json.dumps({'error': error_message})}\n\n"
        else:
            return error_message