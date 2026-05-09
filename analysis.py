import re
import pandas as pd
from datetime import datetime, timedelta
from text_utils import detect_document_language, clean_extracted_text
from llm_utils import query_llm, llm_cleanup_output
import streamlit as st

def generate_summary(text):
    """Generate a comprehensive, detailed summary with explanations from extracted text"""
    # Clean text but preserve ALL languages
    cleaned_text = clean_extracted_text(text)
    doc_lang = detect_document_language(cleaned_text)
    
    # Use full cleaned text — do NOT strip Arabic
    work_text = cleaned_text
    
    # Build language-aware LLM prompt
    if doc_lang == 'arabic':
        lang_instruction = """IMPORTANT: This document is in Arabic. You MUST respond entirely in Arabic.
Use proper Arabic grammar, spelling, and punctuation. Do NOT transliterate or mix languages unless the original text does."""
    else:
        lang_instruction = "Respond in the same language as the document content."
    
    # Try LLM first for better summary
    if bool(st.secrets.get('HF_API_KEY')) and len(work_text) > 50:
        prompt = f"""{lang_instruction}

Analyze this document in detail and create a comprehensive executive summary with explanations.

Structure your response as follows:

1. **Overview**: Provide a 2-3 sentence overview of what this document is about.

2. **Key Objectives**: List and explain the main objectives, goals, or purposes mentioned in the document. Provide context and reasoning for each.

3. **Main Content**: Summarize the core content in detail. Include important details, initiatives, strategies, or processes mentioned.

4. **Stakeholders & Resources**: Identify any mentioned teams, departments, stakeholders, or resources involved.

5. **Important Details**: Highlight any critical information, requirements, constraints, or special considerations.

6. **Implications**: Explain what this means for the organization or project and why it matters.

Document Content:
{work_text[:6000]}

Comprehensive Summary:"""
        llm_summary = query_llm(prompt, max_tokens=2048)
        if llm_summary and len(llm_summary) > 50:
            llm_summary = llm_cleanup_output(llm_summary.strip(), "executive summary of a document")
            return llm_summary
    
    # Fallback to intelligent extraction (more comprehensive)
    # Look for key sections and extract meaningful content
    summary_parts = []
    
    # Extract sentences, handling multiple delimiters (including Arabic question mark)
    sentences = re.split(r'[.!?\u061F\u3002\n]+', work_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    # Prioritize sentences with key terms (English + Arabic)
    priority_terms = ['objective', 'goal', 'strategy', 'initiative', 'platform', 
                      'department', 'ai', 'digital', 'transformation', 'key', 'main',
                      'purpose', 'vision', 'mission', 'target', 'deliver', 'implement',
                      'develop', 'create', 'establish', 'enhance', 'improve', 'focus',
                      # Arabic equivalents
                      '\u0647\u062f\u0641', '\u0627\u0633\u062a\u0631\u0627\u062a\u064a\u062c\u064a\u0629', '\u0645\u0628\u0627\u062f\u0631\u0629', '\u0631\u0624\u064a\u0629', '\u0631\u0633\u0627\u0644\u0629', '\u062a\u0637\u0648\u064a\u0631', '\u062a\u062d\u0633\u064a\u0646',
                      '\u0645\u0634\u0631\u0648\u0639', '\u062e\u0637\u0629', '\u062a\u0646\u0641\u064a\u0630', '\u0625\u062f\u0627\u0631\u0629', '\u0646\u0638\u0627\u0645', '\u062e\u062f\u0645\u0629', '\u062c\u0648\u062f\u0629', '\u0623\u062f\u0627\u0621']
    
    context_terms = ['background', 'overview', 'introduction', 'summary', 'scope',
                     'stakeholder', 'team', 'resource', 'requirement', 'constraint',
                     # Arabic equivalents
                     '\u0645\u0642\u062f\u0645\u0629', '\u0646\u0638\u0631\u0629 \u0639\u0627\u0645\u0629', '\u0645\u0644\u062e\u0635', '\u0646\u0637\u0627\u0642', '\u0641\u0631\u064a\u0642', '\u0645\u0648\u0627\u0631\u062f', '\u0645\u062a\u0637\u0644\u0628\u0627\u062a']
    
    detail_terms = ['include', 'feature', 'component', 'process', 'phase', 'stage',
                    'milestone', 'deliverable', 'output', 'result', 'outcome',
                    # Arabic equivalents
                    '\u064a\u062a\u0636\u0645\u0646', '\u0645\u0643\u0648\u0646', '\u0639\u0645\u0644\u064a\u0629', '\u0645\u0631\u062d\u0644\u0629', '\u0646\u062a\u064a\u062c\u0629', '\u0645\u062e\u0631\u062c\u0627\u062a']
    
    priority_sentences = []
    context_sentences = []
    detail_sentences = []
    other_sentences = []
    
    for s in sentences:
        s = s.strip()
        # Clean stray page/section numbers from start of sentence (e.g. "42 Title" -> "Title")
        s = re.sub(r'^(\d{1,3}|[a-z]{1,2})\s+', '', s, flags=re.IGNORECASE)
        # Also clean Arabic leading numbers
        s = re.sub(r'^[\u0660-\u0669]{1,3}\s+', '', s)
        
        if not s or len(s) < 5:
            continue
            
        s_check = s.lower() if doc_lang != 'arabic' else s
        if any(term in s_check for term in priority_terms):
            priority_sentences.append(s)
        elif any(term in s_check for term in context_terms):
            context_sentences.append(s)
        elif any(term in s_check for term in detail_terms):
            detail_sentences.append(s)
        else:
            other_sentences.append(s)
    
    # Build comprehensive summary with structure (language-aware headers)
    if doc_lang == 'arabic':
        summary = "**📋 نظرة عامة على الوثيقة:**\n"
    else:
        summary = "**📋 Document Overview:**\n"
    
    # Add overview sentences
    overview = context_sentences[:2] if context_sentences else other_sentences[:2]
    for sent in overview:
        sent = sent.strip()
        if not sent.endswith(('.', '!', '?', '\u061F')):
            sent += '.' if doc_lang != 'arabic' else '.'
        summary += f"{sent}\n\n"
    
    # Add key objectives
    if priority_sentences:
        if doc_lang == 'arabic':
            summary += "**🎯 الأهداف الرئيسية:**\n"
        else:
            summary += "**🎯 Key Objectives & Focus Areas:**\n"
        for i, sent in enumerate(priority_sentences[:5], 1):
            sent = sent.strip()
            if not sent.endswith(('.', '!', '?', '\u061F')):
                sent += '.'
            summary += f"{i}. {sent}\n"
        summary += "\n"
    
    # Add important details
    if detail_sentences:
        if doc_lang == 'arabic':
            summary += "**📌 تفاصيل مهمة:**\n"
        else:
            summary += "**📌 Important Details:**\n"
        for sent in detail_sentences[:4]:
            sent = sent.strip()
            if not sent.endswith(('.', '!', '?', '\u061F')):
                sent += '.'
            summary += f"• {sent}\n"
        summary += "\n"
    
    # Add additional context
    if len(other_sentences) > 2:
        if doc_lang == 'arabic':
            summary += "**ℹ️ سياق إضافي:**\n"
        else:
            summary += "**ℹ️ Additional Context:**\n"
        for sent in other_sentences[2:5]:
            sent = sent.strip()
            if not sent.endswith(('.', '!', '?', '\u061F')):
                sent += '.'
            summary += f"• {sent}\n"
    
    if len(summary) > 50:
        # Apply the same cleanup pass used on LLM summaries
        summary = llm_cleanup_output(summary, "executive summary of a document")
        return summary
    
    return "No comprehensive summary could be generated from the document content."

def extract_dates(text):
    """Extract dates mentioned in the document"""
    # Pattern for various date formats
    date_patterns = [
        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # DD/MM/YYYY or MM-DD-YYYY
        r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
    ]
    
    dates_found = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        dates_found.extend(matches)
    
    return list(set(dates_found))

def extract_keywords(text):
    """Extract important keywords/phrases using LLM if available"""
    doc_lang = detect_document_language(text)
    # Try LLM first
    if bool(st.secrets.get('HF_API_KEY')):
        if doc_lang == 'arabic':
            lang_note = "The document is in Arabic. Return the keywords in Arabic."
        else:
            lang_note = "Return keywords in the same language as the document."
        prompt = f"""Extract the 10 most important keywords or key phrases from this document. {lang_note}
Return them as a comma-separated list:

{text[:2000]}

Keywords:"""
        llm_keywords = query_llm(prompt, max_tokens=2048)
        if llm_keywords:
            # Clean up the raw keyword list before parsing
            llm_keywords = llm_cleanup_output(llm_keywords.strip(), "comma-separated keyword list")
            keywords = [k.strip() for k in llm_keywords.split(',') if k.strip()]
            if keywords:
                return keywords[:10]
    
    # Fallback: Common project-related keywords
    keywords = []
    important_terms = [
        'budget', 'timeline', 'deadline', 'milestone', 'phase', 'objective',
        'risk', 'requirement', 'stakeholder', 'deliverable', 'scope',
        'implementation', 'deployment', 'integration', 'compliance', 'governance',
        'strategy', 'digital', 'transformation', 'automation', 'efficiency',
        'innovation', 'performance', 'quality', 'security', 'data'
    ]
    
    text_lower = text.lower()
    for term in important_terms:
        if term in text_lower:
            keywords.append(term.capitalize())
    
    return keywords

def calculate_risk_score(text):
    """Calculate risk score based on document content using LLM if available"""
    doc_lang = detect_document_language(text)
    # Try LLM first for better analysis
    if bool(st.secrets.get('HF_API_KEY')):
        lang_note = "The document may be in Arabic or English. Analyze the content regardless of language." if doc_lang == 'arabic' else ""
        prompt = f"""Analyze this document for project risks. {lang_note}
Rate the overall risk level as LOW, MEDIUM, or HIGH, and provide a score from 1-10 (10 being lowest risk). Format: "LEVEL: X/10"

{text[:2000]}

Risk Assessment:"""
        llm_response = query_llm(prompt, max_tokens=2048)
        if llm_response:
            llm_response = llm_cleanup_output(llm_response.strip(), "risk assessment result with a level label and numeric score")
            # Parse response
            response_lower = llm_response.lower()
            if 'high' in response_lower:
                level = "High"
                score = 3.0
            elif 'low' in response_lower:
                level = "Low"
                score = 8.0
            else:
                level = "Medium"
                score = 5.0

            # Try to extract numeric score
            score_match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', llm_response)
            if score_match:
                score = float(score_match.group(1))

            return round(score, 1), level
    
    # Fallback to rule-based
    risk_indicators = {
        'high_risk': ['urgent', 'critical', 'risk', 'delay', 'issue', 'problem', 'challenge', 'concern', 'failure', 'crisis'],
        'medium_risk': ['consider', 'review', 'assess', 'evaluate', 'potential', 'uncertain', 'unclear'],
        'low_risk': ['complete', 'success', 'achieved', 'approved', 'confirmed', 'stable', 'secure']
    }
    
    text_lower = text.lower()
    high_count = sum(1 for word in risk_indicators['high_risk'] if word in text_lower)
    medium_count = sum(1 for word in risk_indicators['medium_risk'] if word in text_lower)
    low_count = sum(1 for word in risk_indicators['low_risk'] if word in text_lower)
    
    # Calculate weighted score (lower is better)
    total = high_count * 3 + medium_count * 2 + low_count * 1
    if total == 0:
        return 5.0, "Medium"
    
    score = min(10, max(1, 10 - (high_count * 2) + (low_count * 0.5)))
    
    if score >= 7:
        level = "Low"
    elif score >= 4:
        level = "Medium"
    else:
        level = "High"
    
    return round(score, 1), level

def estimate_project_duration(text):
    """Estimate project duration based on content"""
    # Look for duration mentions
    duration_patterns = [
        (r'(\d+)\s*weeks?', 'weeks'),
        (r'(\d+)\s*months?', 'months'),
        (r'(\d+)\s*days?', 'days'),
    ]
    
    for pattern, unit in duration_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            return f"{num} {unit.capitalize()}"
    
    # Default estimate based on document length
    word_count = len(text.split())
    if word_count > 2000:
        return "12-16 Weeks"
    elif word_count > 1000:
        return "8-12 Weeks"
    else:
        return "4-8 Weeks"

def generate_timeline(text):
    """Generate project timeline from document using AI when available"""
    today = datetime.now()
    timeline_data = []
    
    # Try LLM first for intelligent phase extraction
    doc_lang = detect_document_language(text)
    if bool(st.secrets.get('HF_API_KEY')):
        lang_note = "The document may be in Arabic. Extract phase names in English for the timeline chart." if doc_lang == 'arabic' else ""
        prompt = f"""Analyze this project document and extract the project phases/stages with estimated durations. {lang_note}
Format each phase as: "Phase Name | Duration in days"
List 4-6 phases. If durations aren't mentioned, estimate based on complexity.

Document:
{text[:2500]}

Project Phases:"""
        
        llm_response = query_llm(prompt, max_tokens=2048)
        if llm_response:
            llm_response = llm_cleanup_output(llm_response.strip(), "project timeline phase list in 'Phase Name | Duration in days' format")
        if llm_response:
            # Parse LLM response
            lines = llm_response.strip().split('\n')
            current_date = today
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Remove bullet points, numbers at start
                line = re.sub(r'^[\d\.\-\*\•]+\s*', '', line)
                
                # Try to parse "Phase Name | Duration" format
                if '|' in line:
                    parts = line.split('|')
                    phase_name = parts[0].strip()
                    duration_text = parts[1].strip() if len(parts) > 1 else "14"
                    
                    # Extract number from duration
                    duration_match = re.search(r'(\d+)', duration_text)
                    duration = int(duration_match.group(1)) if duration_match else 14
                    
                    # Cap duration to reasonable range
                    duration = max(7, min(90, duration))
                else:
                    # Just phase name, use default duration
                    phase_name = line
                    duration = 14
                
                if phase_name and len(phase_name) > 3:
                    # Determine resource based on phase content
                    phase_lower = phase_name.lower()
                    if any(word in phase_lower for word in ['plan', 'requirement', 'analysis', 'design', 'scope']):
                        resource = "Planning"
                    elif any(word in phase_lower for word in ['test', 'valid', 'qa', 'quality', 'review']):
                        resource = "QA"
                    elif any(word in phase_lower for word in ['deploy', 'handover', 'launch', 'release', 'go-live']):
                        resource = "Operations"
                    elif any(word in phase_lower for word in ['develop', 'implement', 'build', 'code', 'create']):
                        resource = "Development"
                    else:
                        resource = "Execution"
                    
                    start = current_date
                    finish = current_date + timedelta(days=duration)
                    
                    timeline_data.append({
                        'Task': phase_name[:60],  # Limit length
                        'Start': start.strftime('%Y-%m-%d'),
                        'Finish': finish.strftime('%Y-%m-%d'),
                        'Resource': resource
                    })
                    
                    current_date = finish + timedelta(days=1)
            
            # If we got valid phases from LLM, return them
            if len(timeline_data) >= 2:
                return pd.DataFrame(timeline_data)
    
    # Fallback: Try to find phases mentioned in text using regex
    phases = []
    phase_patterns = [
        r'phase\s*(\d+)[:\s]*([^\n.]+)',
        r'step\s*(\d+)[:\s]*([^\n.]+)',
        r'stage\s*(\d+)[:\s]*([^\n.]+)',
        r'milestone\s*(\d+)[:\s]*([^\n.]+)',
    ]
    
    for pattern in phase_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            phases.append(f"Phase {match[0]}: {match[1].strip()[:50]}")
    
    # Also look for numbered lists that might be phases
    numbered_items = re.findall(r'^\s*(\d+)[\.\)]\s*([A-Z][^\n]{10,60})', text, re.MULTILINE)
    if len(numbered_items) >= 3 and not phases:
        for num, item in numbered_items[:6]:
            phases.append(f"Step {num}: {item.strip()}")
    
    # If still no phases found, create default structure based on document content
    if not phases:
        # Analyze content to create relevant default phases
        text_lower = text.lower()
        
        if 'digital' in text_lower or 'transformation' in text_lower:
            phases = [
                "Phase 1: Assessment & Strategy",
                "Phase 2: Digital Infrastructure Setup",
                "Phase 3: Implementation & Integration",
                "Phase 4: Testing & Optimization",
                "Phase 5: Deployment & Training"
            ]
        elif 'software' in text_lower or 'development' in text_lower:
            phases = [
                "Phase 1: Requirements Gathering",
                "Phase 2: Design & Architecture",
                "Phase 3: Development",
                "Phase 4: Testing & QA",
                "Phase 5: Deployment & Support"
            ]
        else:
            phases = [
                "Phase 1: Initiation & Planning",
                "Phase 2: Analysis & Design",
                "Phase 3: Execution",
                "Phase 4: Monitoring & Control",
                "Phase 5: Closure & Handover"
            ]
    
    # Generate timeline data with varied durations
    current_date = today
    base_duration = 14  # 2 weeks base
    
    for i, phase in enumerate(phases[:6]):  # Max 6 phases
        # Vary duration based on phase type
        phase_lower = phase.lower()
        if 'plan' in phase_lower or 'requirement' in phase_lower or 'analysis' in phase_lower:
            duration = base_duration  # 2 weeks for planning
        elif 'develop' in phase_lower or 'implement' in phase_lower or 'execution' in phase_lower:
            duration = base_duration * 2  # 4 weeks for development
        elif 'test' in phase_lower or 'qa' in phase_lower:
            duration = int(base_duration * 1.5)  # 3 weeks for testing
        else:
            duration = base_duration
        
        start = current_date
        finish = current_date + timedelta(days=duration)
        
        # Determine resource based on phase
        if 'plan' in phase_lower or 'requirement' in phase_lower or 'analysis' in phase_lower:
            resource = "Planning"
        elif 'test' in phase_lower or 'valid' in phase_lower or 'qa' in phase_lower:
            resource = "QA"
        elif 'deploy' in phase_lower or 'handover' in phase_lower or 'closure' in phase_lower:
            resource = "Operations"
        elif 'develop' in phase_lower or 'implement' in phase_lower:
            resource = "Development"
        else:
            resource = "Execution"
        
        timeline_data.append({
            'Task': phase,
            'Start': start.strftime('%Y-%m-%d'),
            'Finish': finish.strftime('%Y-%m-%d'),
            'Resource': resource
        })
        
        current_date = finish + timedelta(days=1)
    
    return pd.DataFrame(timeline_data)

def analyze_go_nogo(text):
    """Perform Go/No-Go analysis using LLM for intelligent decision making"""
    criteria = {}
    ai_reasoning = ""
    ai_verdict = None
    
    # Try LLM for comprehensive AI-driven analysis
    doc_lang = detect_document_language(text)
    if bool(st.secrets.get('HF_API_KEY')):
        lang_note = "The document may be in Arabic. Analyze its content regardless of language. Respond with scores in the exact format below (in English)." if doc_lang == 'arabic' else ""
        # First prompt: Get detailed scores with reasoning
        score_prompt = f"""Analyze this project document for a Go/No-Go decision. {lang_note}

Rate each criterion from 1-10 (1=very poor, 10=excellent):
- Technical Feasibility: Can the project be technically implemented?
- Budget Availability: Are financial resources adequate?
- Resource Readiness: Are team and skills available?
- Stakeholder Alignment: Is there executive support?

Format your response as:
Technical Feasibility: X/10
Budget Availability: X/10
Resource Readiness: X/10
Stakeholder Alignment: X/10
Verdict: GO or NO-GO or CONDITIONAL

Document:
{text[:2500]}

Analysis:"""
        
        llm_response = query_llm(score_prompt, max_tokens=2048)
        if llm_response:
            llm_response = llm_cleanup_output(llm_response.strip(), "Go/No-Go decision analysis with criterion scores and a verdict")
        if llm_response:
            ai_reasoning = llm_response
            
            # Parse scores using multiple patterns for robustness
            score_patterns = [
                (r'Technical\s*Feasibility[:\s]*(\d+)', 'Technical Feasibility'),
                (r'Budget\s*Availability[:\s]*(\d+)', 'Budget Availability'),
                (r'Resource\s*Readiness[:\s]*(\d+)', 'Resource Readiness'),
                (r'Stakeholder\s*Alignment[:\s]*(\d+)', 'Stakeholder Alignment'),
            ]
            
            for pattern, criterion in score_patterns:
                match = re.search(pattern, llm_response, re.IGNORECASE)
                if match:
                    score = int(match.group(1))
                    criteria[criterion] = min(10, max(1, score))
            
            # Also try simpler number extraction if structured format fails
            if len(criteria) < 4:
                # Look for any numbers in the response
                numbers = re.findall(r'\b(\d+)\s*/\s*10', llm_response)
                if not numbers:
                    numbers = re.findall(r'\b([1-9]|10)\b', llm_response)
                
                criterion_names = ['Technical Feasibility', 'Budget Availability', 'Resource Readiness', 'Stakeholder Alignment']
                for i, criterion in enumerate(criterion_names):
                    if criterion not in criteria and i < len(numbers):
                        criteria[criterion] = min(10, max(1, int(numbers[i])))
            
            # Parse verdict from AI response
            response_lower = llm_response.lower()
            if 'no-go' in response_lower or 'nogo' in response_lower or 'not recommended' in response_lower:
                ai_verdict = "NO-GO"
            elif 'conditional' in response_lower or 'with conditions' in response_lower or 'pending' in response_lower:
                ai_verdict = "CONDITIONAL"
            elif 'go' in response_lower and 'no-go' not in response_lower:
                ai_verdict = "GO"
    
    # Fill in missing criteria with AI-informed fallback
    text_lower = text.lower()
    
    if 'Technical Feasibility' not in criteria:
        # Analyze technical indicators
        tech_positive = ['proven', 'established', 'available', 'existing', 'ready', 'mature', 'stable']
        tech_negative = ['complex', 'new technology', 'untested', 'experimental', 'challenging', 'difficult']
        positive_count = sum(1 for k in tech_positive if k in text_lower)
        negative_count = sum(1 for k in tech_negative if k in text_lower)
        tech_keywords = ['technical', 'technology', 'system', 'platform', 'infrastructure', 'integration', 'ai', 'digital']
        base_score = 5 + min(3, sum(1 for k in tech_keywords if k in text_lower))
        criteria['Technical Feasibility'] = min(10, max(1, base_score + positive_count - negative_count))
    
    if 'Budget Availability' not in criteria:
        # Analyze budget indicators
        budget_positive = ['funded', 'approved', 'allocated', 'sufficient', 'available', 'secured']
        budget_negative = ['limited', 'constraint', 'shortage', 'insufficient', 'unfunded', 'pending approval']
        positive_count = sum(1 for k in budget_positive if k in text_lower)
        negative_count = sum(1 for k in budget_negative if k in text_lower)
        budget_keywords = ['budget', 'cost', 'fund', 'invest', 'financial', 'capital']
        base_score = 5 + min(2, sum(1 for k in budget_keywords if k in text_lower))
        criteria['Budget Availability'] = min(10, max(1, base_score + positive_count - negative_count))
    
    if 'Resource Readiness' not in criteria:
        # Analyze resource indicators
        resource_positive = ['experienced', 'skilled', 'trained', 'qualified', 'available', 'dedicated', 'capable']
        resource_negative = ['shortage', 'hiring', 'training needed', 'gap', 'lack', 'insufficient']
        positive_count = sum(1 for k in resource_positive if k in text_lower)
        negative_count = sum(1 for k in resource_negative if k in text_lower)
        resource_keywords = ['team', 'staff', 'resource', 'personnel', 'expert', 'skill']
        base_score = 4 + min(2, sum(1 for k in resource_keywords if k in text_lower))
        criteria['Resource Readiness'] = min(10, max(1, base_score + positive_count - negative_count))
    
    if 'Stakeholder Alignment' not in criteria:
        # Analyze stakeholder indicators
        stakeholder_positive = ['approved', 'supported', 'endorsed', 'committed', 'aligned', 'agreed']
        stakeholder_negative = ['opposition', 'concern', 'resistance', 'disagreement', 'pending', 'unclear']
        positive_count = sum(1 for k in stakeholder_positive if k in text_lower)
        negative_count = sum(1 for k in stakeholder_negative if k in text_lower)
        stakeholder_keywords = ['stakeholder', 'sponsor', 'executive', 'management', 'leadership', 'board']
        base_score = 5 + min(2, sum(1 for k in stakeholder_keywords if k in text_lower))
        criteria['Stakeholder Alignment'] = min(10, max(1, base_score + positive_count - negative_count))
    
    # Calculate overall score and determine verdict (forgiving thresholds)
    avg_score = sum(criteria.values()) / len(criteria)
    
    # Use AI verdict if available, otherwise calculate based on scores
    if ai_verdict:
        verdict = f"{ai_verdict} {'✅' if ai_verdict == 'GO' else '❌' if ai_verdict == 'NO-GO' else '⚠️'}"
        # Adjust confidence based on score alignment with AI verdict
        if ai_verdict == "GO" and avg_score >= 5:
            confidence = int(min(95, avg_score * 10 + 15))
        elif ai_verdict == "NO-GO" and avg_score < 3:
            confidence = int(min(95, (10 - avg_score) * 10 + 10))
        elif ai_verdict == "CONDITIONAL":
            confidence = int(avg_score * 10 + 10)
        else:
            confidence = int(avg_score * 9)  # More forgiving when AI and scores disagree
    else:
        # Score-based verdict (more forgiving thresholds)
        if avg_score >= 5:  # Lowered from 7 - easier to get GO
            verdict = "GO ✅"
            confidence = int(min(95, avg_score * 10 + 10))
        elif avg_score >= 3:  # Lowered from 5 - wider CONDITIONAL range
            verdict = "CONDITIONAL ⚠️"
            confidence = int(avg_score * 10 + 15)
        else:  # Only NO-GO if really low (below 3)
            verdict = "NO-GO ❌"
            confidence = int((10 - avg_score) * 7)
    
    return criteria, verdict, confidence
