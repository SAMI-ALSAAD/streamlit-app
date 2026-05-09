import re
import unicodedata

def fix_fused_arabic_words(text):
    """Split Arabic words that were fused with common prepositions/conjunctions during extraction.
    
    This uses high-confidence rules:
    1. 'ة' (Teh Marbuta) never connects to the left and only appears at word ends.
    2. Specific common fusions like 'التيتم' and 'الفائزأن'.
    """
    if not text:
        return text
    
    AR = '[\u0600-\u06FF]'
    
    # 1. THE TEH-MARBUTA RULE (100% Confidence): 
    # 'ة' ONLY ever appears at the very end of a word.
    text = re.sub(rf'(ة)({AR})', r'\1 \2', text)
    
    # 2. THE 'AL-TI' RULE: 'التي' (which) is often fused with 'تم' (was/completed)
    text = re.sub(rf'(التي)(تم|كان|بدأ|يتم)', r'\1 \2', text)
    
    # 3. COMMON PREPOSITION FUSIONS (e.g., 'الفائزأن' -> 'الفائز أن')
    # Only split if the transition is likely a fusion error
    fused_suffixes = ['أن', 'في', 'من', 'عن']
    for word in fused_suffixes:
        # Match word ending in common consonants followed by a preposition
        pattern = rf'({AR}{{3,}}[رزدذو])({word})(?=\s|$)'
        text = re.sub(pattern, r'\1 \2', text)
        
    return text

def clean_extracted_text(text):
    """Clean and normalize extracted text, handling mixed language concatenation"""
    if not text:
        return ""
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKC', text)
    
    # Remove zero-width characters first
    text = re.sub(r'[\u200b\u200c\u200d\ufeff\u00ad]', '', text)
    
    # Remove control characters except newlines and tabs
    text = ''.join(char for char in text if unicodedata.category(char) != 'Cc' or char in '\n\t')
    
    # Apply fused word fix
    text = fix_fused_arabic_words(text)
    
    # Add space between Arabic and Latin characters (handles concatenation)
    text = re.sub(r'([\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF])([A-Za-z0-9])', r'\1 \2', text)
    text = re.sub(r'([A-Za-z0-9])([\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF])', r'\1 \2', text)
    
    # Standardize quotes
    text = text.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
    
    # Clean up multiple spaces
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Clean up multiple newlines (keep max 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Clean up lines
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def extract_english_only(text):
    """Extract only English text from mixed content"""
    # Split on whitespace and filter
    words = text.split()
    english_parts = []
    for word in words:
        if word.strip() and not re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', word):
            english_parts.append(word.strip())
    return ' '.join(english_parts)

def detect_document_language(text):
    """Detect the dominant language of the document text.
    Returns 'arabic' if Arabic characters dominate, otherwise 'english'."""
    if not text:
        return 'english'
    arabic_chars = len(re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text))
    latin_chars = len(re.findall(r'[A-Za-z]', text))
    if arabic_chars > latin_chars:
        return 'arabic'
    return 'english'
