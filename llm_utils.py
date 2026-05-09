import requests
import streamlit as st
from config import LLM_MODEL

def query_llm(prompt, max_tokens=2048):
    """Query HuggingFace inference API with provided API key."""
    api_key = st.secrets.get("HF_API_KEY", "").strip()
    if not api_key:
        return None
    
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        # Format prompt with ChatML for Qwen models
        if "Qwen" in LLM_MODEL:
            formatted_prompt = f"<|im_start|>system\nYou are a helpful AI assistant.<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
        else:
            formatted_prompt = prompt
        
        # Use HuggingFace inference API
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{LLM_MODEL}",
            headers=headers,
            json={
                "inputs": formatted_prompt, 
                "parameters": {
                    "max_new_tokens": max_tokens,
                    "temperature": 0.3,
                    "do_sample": True,
                    "return_full_text": False
                },
                "options": {"wait_for_model": True}
            },
            timeout=180
        )
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('generated_text', '')
            elif isinstance(result, dict) and 'generated_text' in result:
                return result['generated_text']
            return str(result)
        elif response.status_code == 503:
            # Model is loading, wait and retry once
            import time
            time.sleep(30)
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{LLM_MODEL}",
                headers=headers,
                json={
                    "inputs": formatted_prompt, 
                    "parameters": {
                        "max_new_tokens": max_tokens,
                        "temperature": 0.3,
                        "do_sample": True,
                        "return_full_text": False
                    }
                },
                timeout=120
            )
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('generated_text', '')
        return None
    except Exception:
        return None

def llm_cleanup_output(text, context_hint=""):
    """Send LLM-generated text back to the LLM for a final fix-and-clean-up pass.

    Corrects grammar, formatting, consistency, and removes artefacts introduced
    during the first generation pass.  Returns the cleaned text, or the
    original if the LLM is unavailable or the cleanup result is too short.

    Args:
        text: The LLM-generated text to clean up.
        context_hint: Optional one-line description of what the text represents
                      (e.g. "executive summary", "keyword list") so the LLM
                      knows how to treat it.
    """
    api_key = st.secrets.get("HF_API_KEY", "").strip()
    if not api_key or not text or not text.strip():
        return text

    hint_line = f"The text below is a {context_hint}. " if context_hint else ""
    prompt = f"""You are a professional editor specialising in Arabic and English documents. \
{hint_line}The text was extracted from a PDF and then processed by an AI; it may still contain \
residual extraction artefacts. Fix ALL of the following issues:

1. Grammar, spelling, and punctuation — correct any errors in any language present.
2. Fused / run-together words — insert the missing space where words were accidentally joined \
(e.g. "الحكوميةفي" → "الحكومية في", "الفائزأن" → "الفائز أن", "التيتم" → "التي تم").
3. Stray numbers — remove isolated numbers that appear to be page numbers, article numbers, or \
section references that were prepended to a phrase and are NOT part of the sentence meaning \
(e.g. "42 متطلبات" where 42 is a page number). Keep numbers that are genuinely part of the \
content (dates, quantities, percentages, etc.).
4. Nonsensical or incomplete sentences — either complete them if the meaning is recoverable \
from context, or remove them entirely if they cannot be salvaged.
5. Duplicate or redundant sentences — remove duplicates.
6. Consistent formatting — preserve bullet points, numbered lists, and section headings; \
fix spacing and indentation.

Rules you MUST follow:
- Do NOT invent new information or change the meaning of correct text.
- Do NOT add any explanation or commentary.
- Return ONLY the corrected text.

Text to fix:
{text}

Corrected text:"""

    cleaned = query_llm(prompt, max_tokens=2048)
    # Accept the cleaned version only if it is substantive
    if cleaned and len(cleaned.strip()) > len(text) * 0.3:
        return cleaned.strip()
    return text
