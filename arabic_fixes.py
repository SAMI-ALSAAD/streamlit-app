import re
import unicodedata
import streamlit as st
from llm_utils import query_llm, get_api_key
from text_utils import detect_document_language

def fix_arabic_pdf_text(text):
    """Fix reversed Arabic text from PDF extraction."""
    if not text:
        return text
    
    # IMPORTANT: Decompose Arabic Presentation Form ligatures (e.g. U+FEFB ﻻ → ل+ا)
    # BEFORE reversal, so each character reverses independently
    text = unicodedata.normalize('NFKC', text)
    
    # Check if text even contains Arabic characters
    arabic_words = re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+', text)
    if not arabic_words or len(arabic_words) < 2:
        return text
    
    # --- Detect if text is reversed ---
    starts_with_al = sum(1 for w in arabic_words if w.startswith('\u0627\u0644'))
    ends_with_al_reversed = sum(1 for w in arabic_words if w.endswith('\u0644\u0627') and len(w) > 2)
    ends_with_ta = sum(1 for w in arabic_words if w.endswith('\u0629'))
    starts_with_ta = sum(1 for w in arabic_words if w.startswith('\u0629') and len(w) > 1)
    
    correct_indicators = starts_with_al + ends_with_ta
    reversed_indicators = ends_with_al_reversed + starts_with_ta
    
    if reversed_indicators <= correct_indicators:
        return text  # Text appears to already be in correct order
    
    # --- Fix reversed text line by line ---
    mirror_chars = {
        ')': '(', '(': ')',
        ']': '[', '[': ']',
        '}': '{', '{': '}',
        '\u00bb': '\u00ab', '\u00ab': '\u00bb',
        '\ufd3e': '\ufd3f', '\ufd3f': '\ufd3e',
    }
    
    fixed_lines = []
    for line in text.split('\n'):
        if not line.strip():
            fixed_lines.append(line)
            continue
        
        arabic_char_count = len(re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', line))
        
        if arabic_char_count < 2:
            fixed_lines.append(line)
            continue
        
        words = line.split()
        fixed_words = []
        
        for word in words:
            has_arabic = bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', word))
            if has_arabic:
                reversed_word = word[::-1]
                reversed_word = ''.join(mirror_chars.get(c, c) for c in reversed_word)
                fixed_words.append(reversed_word)
            else:
                fixed_words.append(word)
        
        fixed_words.reverse()
        fixed_lines.append(' '.join(fixed_words))
    
    result = '\n'.join(fixed_lines)
    
    # Apply lam-alef ligature fixes after reversal
    result = fix_lam_alef_in_text(result)
    
    return result

def fix_lam_alef_in_text(text):
    """Fix broken lam-alef (لا) sequences that appear as alef-lam (ال) inside words."""
    if not text:
        return text
    
    ARABIC_RANGE = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]'
    
    def fix_word(match):
        word = match.group(0)
        if len(word) < 3:
            return word
        
        # --- Fix Pattern 2 first: امل → الم (broken definite article) ---
        preposition_prefixes = '\u0628\u0641\u0648\u0644\u0643\u0633'
        
        fixed = word
        if (len(fixed) > 4 and fixed[0] in preposition_prefixes 
                and fixed[1] == '\u0627' and fixed[2] != '\u0644'):
            rest = fixed[2:]
            lam_pos = rest.find('\u0644')
            if lam_pos == 1:  # e.g. امل → swap to الم
                fixed = fixed[0] + '\u0627\u0644' + rest[0] + rest[2:]
        elif (len(fixed) > 3 and fixed[0] == '\u0627' and fixed[1] != '\u0644'):
            rest = fixed[1:]
            lam_pos = rest.find('\u0644')
            if lam_pos == 1:  # e.g. امل → swap to الم
                fixed = '\u0627\u0644' + rest[0] + rest[2:]
        
        # --- Fix Pattern 1: ال inside word → لا ---
        if fixed.startswith('\u0627\u0644'):
            interior_start = 2
        elif (len(fixed) > 3 and fixed[0] in preposition_prefixes 
                and fixed[1:3] == '\u0627\u0644'):
            interior_start = 3
        else:
            interior_start = 0
        
        if interior_start < len(fixed):
            prefix = fixed[:interior_start]
            interior = fixed[interior_start:]
            interior = interior.replace('\u0627\u0644', '\u0644\u0627')
            fixed = prefix + interior
        
        return fixed
    
    return re.sub(ARABIC_RANGE + r'+', fix_word, text)

def llm_correct_arabic_text(text):
    """Use LLM to fix remaining Arabic PDF extraction artifacts."""
    api_key = get_api_key()
    if not api_key:
        return text
    
    doc_lang = detect_document_language(text)
    if doc_lang != 'arabic':
        return text
    
    max_chunk_chars = 2500
    lines = text.split('\n')
    chunks = []
    current_chunk_lines = []
    current_length = 0
    
    for line in lines:
        if current_length + len(line) + 1 > max_chunk_chars and current_chunk_lines:
            chunks.append('\n'.join(current_chunk_lines))
            current_chunk_lines = [line]
            current_length = len(line)
        else:
            current_chunk_lines.append(line)
            current_length += len(line) + 1
    
    if current_chunk_lines:
        chunks.append('\n'.join(current_chunk_lines))
    
    corrected_chunks = []
    for chunk in chunks:
        prompt = f"""النص التالي مستخرج من ملف PDF ويحتوي على أخطاء استخراج. صحّح الأخطاء التالية فقط:
- إصلاح حرف اللام-ألف المكسور (مثال: "املنافسة" صححها إلى "المنافسة")
- دمج الكلمات المقسومة بمسافات زائدة (مثال: "الخدما ت" صححها إلى "الخدمات")
- إصلاح الأحرف المشوهة أو المبدلة

قواعد مهمة:
- أعد النص المصحح فقط بدون أي شرح أو تعليق
- حافظ على نفس البنية وعلامات الترقيم والأرقام والنص الإنجليزي
- لا تضف أو تحذف أي محتوى

النص:
{chunk}

النص المصحح:"""
        
        result = query_llm(prompt, max_tokens=2048)
        if result and len(result.strip()) > len(chunk) * 0.3:
            corrected_chunks.append(result.strip())
        else:
            corrected_chunks.append(chunk)
    
    return '\n'.join(corrected_chunks)

def fix_split_arabic_words(text):
    """Merge Arabic words that were incorrectly split by the PDF extractor."""
    if not text:
        return text
    
    AR = '[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]'
    
    text = re.sub(
        rf'({AR}{{3,}})\s+({AR}{{1,2}})(?=\s|$|[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF])',
        r'\1\2',
        text
    )
    
    text = re.sub(
        rf'(?:^|\s)({AR}{{1,2}})\s+({AR}{{3,}})',
        r' \1\2',
        text
    )
    
    return text.strip()
