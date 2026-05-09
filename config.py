import requests

# Document extraction libraries
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

# Translation library
try:
    from deep_translator import GoogleTranslator
    TRANSLATION_SUPPORT = True
except ImportError:
    TRANSLATION_SUPPORT = False

# Language codes mapping (used across translation functions)
LANG_CODES = {
    "Arabic": "ar", "English": "en", "French": "fr", "Spanish": "es",
    "German": "de", "Italian": "it", "Portuguese": "pt", "Russian": "ru",
    "Chinese (Simplified)": "zh-CN", "Chinese (Traditional)": "zh-TW",
    "Japanese": "ja", "Korean": "ko", "Hindi": "hi", "Turkish": "tr",
    "Dutch": "nl", "Polish": "pl", "Swedish": "sv", "Indonesian": "id",
    "Thai": "th", "Vietnamese": "vi", "Hebrew": "he", "Persian": "fa",
    "Urdu": "ur", "Bengali": "bn", "Greek": "el"
}

# RTL (Right-to-Left) languages
RTL_LANGUAGES = {"Arabic", "Hebrew", "Persian", "Urdu"}

# Free Cloud LLM Support (HuggingFace free tier - no API key needed)
LLM_AVAILABLE = False

# Qwen2.5-1.5B-Instruct - Highly capable small model, more likely to be available on free tier without token
LLM_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

# Use HuggingFace Inference API (free tier, no key required)
try:
    test_response = requests.post(
        f"https://api-inference.huggingface.co/models/{LLM_MODEL}",
        json={"inputs": "test", "options": {"wait_for_model": True}},
        timeout=30
    )
    if test_response.status_code in [200, 503]:  # 503 means model loading
        LLM_AVAILABLE = True
except Exception:
    pass
