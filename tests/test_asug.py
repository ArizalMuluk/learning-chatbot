import unittest
from utils.asug import get_ai_suggestion

class TestGetAISuggestion(unittest.TestCase):

    def test_valid_input(self):
        user_input = "Apa itu Python?"
        expected_response = "Anda bertanya: 'Apa itu Python?'. (Balasan dari AI akan muncul di sini setelah API Groq diimplementasikan)"
        self.assertEqual(get_ai_suggestion(user_input), expected_response)

    def test_empty_input(self):
        user_input = ""
        expected_response = "Anda bertanya: ''. (Balasan dari AI akan muncul di sini setelah API Groq diimplementasikan)"
        self.assertEqual(get_ai_suggestion(user_input), expected_response)

    def test_long_input(self):
        user_input = "Jelaskan tentang pengembangan perangkat lunak dan metodologi yang digunakan dalam proses tersebut."
        expected_response = "Anda bertanya: 'Jelaskan tentang pengembangan perangkat lunak dan metodologi yang digunakan dalam proses tersebut.'. (Balasan dari AI akan muncul di sini setelah API Groq diimplementasikan)"
        self.assertEqual(get_ai_suggestion(user_input), expected_response)

if __name__ == '__main__':
    unittest.main()