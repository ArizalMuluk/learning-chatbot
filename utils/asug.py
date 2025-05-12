def get_ai_suggestion(user_input):
    """
    Fungsi ini akan berinteraksi dengan AI API untuk mendapatkan respons dalam Bahasa Indonesia
    dan memproteksi dari kata kasar serta unsur pelecehan seksual.
    """
    import os
    import requests
    import re

    # Daftar kata kasar dan pelecehan (bisa dikembangkan)
    banned_words = [
        "anjing", "bangsat", "kontol", "memek", "pepek", "ngentot", "tolol", "babi", "asu",
        "fuck", "bitch", "dick", "pussy", "sex", "seks", "bokep", "mesum", "sange", "bugil"
    ]
    pattern = re.compile(r'\b(' + '|'.join(banned_words) + r')\b', re.IGNORECASE)
    if pattern.search(user_input):
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
                    "Jika ada permintaan yang mengandung kata kasar, pelecehan, atau permintaan tidak pantas, "
                    "tolak dengan sopan."
                ),
            },
            {
                "role": "user",
                "content": user_input,
            }
        ],
        "model": "llama3-8b-8192"
    }

    headers = {
        "Authorization": f"Bearer {API_GROQ}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Maaf, terjadi masalah koneksi ke AI: {e}"

    ai_response = response.json()
    return ai_response['choices'][0]['message']['content']

# Example usage (for testing this module independently)
if __name__ == "__main__":
    test_input = "Jelaskan teorema Pythagoras"
    response = get_ai_suggestion(test_input)
    print(f"AI Response: {response}")