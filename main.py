import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import os
import re

from config import LANG_CODES, DOCX_SUPPORT
from text_utils import clean_extracted_text
from document_extraction import extract_text
from llm_utils import get_api_key
from analysis import (
    generate_summary, 
    extract_dates, 
    extract_keywords, 
    calculate_risk_score, 
    estimate_project_duration, 
    generate_timeline, 
    analyze_go_nogo
)
from translation import (
    translate_text, 
    translate_docx_inplace, 
    translate_pptx_inplace, 
    create_translated_docx, 
    create_translated_pptx
)

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Digital Transformation Hub",
    page_icon="🟩",
    layout="wide"
)

# --- 2. LOAD CSS AND PATTERN BORDERS ---
def load_css():
    if os.path.exists("style.css"):
        with open("style.css") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

def load_pattern_borders():
    """Inject pattern border elements as HTML divs"""
    pattern_path = "pattern.png"
    if os.path.exists(pattern_path):
        with open(pattern_path, "rb") as img_file:
            pattern_base64 = base64.b64encode(img_file.read()).decode()
        
        pattern_html = f'''
        <div class="pattern-border pattern-border-left" 
             style="background-image: url('data:image/png;base64,{pattern_base64}');"></div>
        <div class="pattern-border pattern-border-right" 
             style="background-image: url('data:image/png;base64,{pattern_base64}');"></div>
        <div class="pattern-border-horizontal pattern-border-top" 
             style="background-image: url('data:image/png;base64,{pattern_base64}');"></div>
        <div class="pattern-border-horizontal pattern-border-bottom" 
             style="background-image: url('data:image/png;base64,{pattern_base64}');"></div>
        '''
        st.markdown(pattern_html, unsafe_allow_html=True)

load_css()
load_pattern_borders()


# --- 3. MAIN INTERFACE ---

# Header Section with logos (always visible)
col1, col2 = st.columns([5, 1])
with col1:
    st.image("https://placehold.co/250x80/000000/FFFFFF?text=Intelligent+Solution", width=250)
    st.markdown("**Digital Transformation Enabler** | Fast-Track Solution Rebuild")
with col2:
    # DC Logo placeholder on the right
    if os.path.exists("icon.png"):
        st.image("icon.png", width=100)

# Initialize session state for user ID
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# User ID Entry Screen
if st.session_state.user_id is None:
    st.markdown("---")
    
    # Center the ID input using columns
    col_left, col_center, col_right = st.columns([1, 1, 1])
    with col_center:
        st.markdown("### Please enter your ID")
        with st.form("user_id_form", clear_on_submit=False):
            st.markdown('<div class="id-input-container">', unsafe_allow_html=True)
            user_id_input = st.text_input("Enter your ID", placeholder="Enter any ID...", label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
            submitted = st.form_submit_button("Continue", type="primary", use_container_width=True)
            if submitted:
                if user_id_input.strip():
                    st.session_state.user_id = user_id_input.strip()
                    st.rerun()
                else:
                    st.error("Please enter a valid ID")
    
    st.stop()  # Stop execution here until ID is entered

# Language options - derive from LANG_CODES constant
languages = list(LANG_CODES.keys())

# Main Content Area
st.markdown("### 1. Document Ingestion")

col_left, col_upload, col_right = st.columns([1, 2, 1])
with col_upload:
    uploaded_file = st.file_uploader("Upload Document", type=['pdf', 'docx', 'pptx', 'ppt'], label_visibility="collapsed")
    st.markdown("**Target language**")
    target_lang = st.selectbox("Target Language", languages, label_visibility="collapsed")

if uploaded_file:
    # REAL DOCUMENT PROCESSING
    with st.spinner('Extracting text from document...'):
        extracted_text, error = extract_text(uploaded_file)
    
    if error:
        st.error(error)
    elif not extracted_text or len(extracted_text.strip()) < 10:
        st.warning("Could not extract meaningful text from the document. Please check the file.")
    else:
        # Text is already cleaned by extract functions, but ensure it's clean
        extracted_text = clean_extracted_text(extracted_text)
        
        if bool(get_api_key()):
            st.success(f"✨ AI Strategic Analysis Active (ChatGPT)")
        else:
            st.info("📊 Basic Analysis Mode (AI fallback active. Add OPENAI_API_KEY to secrets for better results)")
            
        st.markdown("---")
        
        # --- REAL ANALYSIS ---
        with st.spinner('Analyzing document content...'):
            # Calculate all metrics
            risk_score, risk_level = calculate_risk_score(extracted_text)
            duration = estimate_project_duration(extracted_text)
            keywords = extract_keywords(extracted_text)
            dates_found = extract_dates(extracted_text)
            criteria, verdict, confidence = analyze_go_nogo(extracted_text)
        
        # --- DASHBOARD LAYOUT ---
        st.markdown("### 2. Strategic Analysis")
        
        # Main Navigation Tabs (replacing metric boxes)
        tab_summary, tab_timeline, tab_decision, tab_translation, tab_risk = st.tabs([
            "📄 Executive Summary", 
            "📅 Project Timeline", 
            "⚖️ Go/No-Go Analysis",
            "🌐 Translation",
            "🛡️ Risk Management"
        ])

        with tab_summary:
            st.subheader("Auto-Generated Summary")
            summary = generate_summary(extracted_text)
            
            # Check if text contains Arabic characters
            has_arabic = bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', summary))
            
            # Build summary HTML with proper bidi handling
            summary_lines = summary.split('\n')
            summary_html_parts = []
            for line in summary_lines:
                stripped = line.strip()
                if not stripped:
                    continue
                # Use dir="auto" so the browser picks RTL or LTR per paragraph
                summary_html_parts.append(f'<p dir="auto" style="margin:0 0 8px 0;">{stripped}</p>')
            
            summary_inner = '\n'.join(summary_html_parts)
            
            # Set overall container direction for Arabic-heavy documents
            dir_attr = 'rtl' if has_arabic else 'ltr'
            summary_class = 'summary-box summary-box-rtl' if has_arabic else 'summary-box'
            
            st.markdown(
                f"<div class='{summary_class}' dir='{dir_attr}'>{summary_inner}</div>",
                unsafe_allow_html=True
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("📌 Key Topics Detected")
                if keywords:
                    # Create styled HTML table for key topics
                    table_html = """
                    <table class="styled-table">
                        <thead>
                            <tr>
                                <th>Key Topic</th>
                            </tr>
                        </thead>
                        <tbody>
                    """
                    for kw in keywords:
                        table_html += f"<tr><td>{kw}</td></tr>"
                    table_html += "</tbody></table>"
                    st.markdown(table_html, unsafe_allow_html=True)
                else:
                    st.write("No specific project keywords detected.")
            
            with col_b:
                st.subheader("📅 Dates Mentioned")
                if dates_found:
                    # Create styled HTML table for dates
                    table_html = """
                    <table class="styled-table-dates">
                        <thead>
                            <tr>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody>
                    """
                    for d in dates_found[:10]:
                        table_html += f"<tr><td>{d}</td></tr>"
                    table_html += "</tbody></table>"
                    st.markdown(table_html, unsafe_allow_html=True)
                else:
                    st.write("No specific dates found in document.")

        with tab_timeline:
            st.subheader("Auto-Generated Project Timeline")
            timeline_df = generate_timeline(extracted_text)
            
            if timeline_df is not None and not timeline_df.empty:
                fig = px.timeline(
                    timeline_df, 
                    x_start="Start", 
                    x_end="Finish", 
                    y="Task", 
                    color="Resource", 
                    color_discrete_sequence=["#4a5568", "#718096", "#a0aec0", "#cbd5e0"]
                )
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(
                    height=400,
                    paper_bgcolor='#f8f9fa',
                    plot_bgcolor='#ffffff',
                    font=dict(size=14),
                    margin=dict(l=10, r=10, t=10, b=10)
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("Timeline Details")
                # Style the timeline details table
                timeline_html = """
                <table class="timeline-table">
                    <thead>
                        <tr>
                """
                for col in timeline_df.columns:
                    timeline_html += f"<th>{col}</th>"
                timeline_html += "</tr></thead><tbody>"
                
                for _, row in timeline_df.iterrows():
                    timeline_html += "<tr>"
                    for col in timeline_df.columns:
                        timeline_html += f"<td>{row[col]}</td>"
                    timeline_html += "</tr>"
                
                timeline_html += "</tbody></table>"
                st.markdown(timeline_html, unsafe_allow_html=True)
            else:
                st.write("Could not generate a project timeline.")

        with tab_decision:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("Evaluation Criteria")
                for criterion, score in criteria.items():
                    col_name, col_score, col_bar = st.columns([2, 1, 2])
                    col_name.write(f"**{criterion}:**")
                    col_score.write(f"{score}/10")
                    col_bar.progress(score / 10)
            
            with c2:
                st.subheader("Verdict")
                if "GO ✅" in verdict:
                    st.success(f"# {verdict}")
                elif "NO-GO" in verdict:
                    st.error(f"# {verdict}")
                else:
                    st.warning(f"# {verdict}")
                st.caption(f"Confidence: {confidence}%")

        with tab_risk:
            st.subheader("🛡️ Risk Management Dashboard")
            
            # Risk Overview Section
            col_risk1, col_risk2, col_risk3 = st.columns(3)
            
            with col_risk1:
                # Risk Score Gauge
                risk_color = "#43A047" if risk_level == "Low" else "#FFA726" if risk_level == "Medium" else "#EF5350"
                st.metric(
                    label="Overall Risk Score",
                    value=f"{risk_score}/10",
                    delta=f"{risk_level} Risk"
                )
            
            with col_risk2:
                st.metric(
                    label="Project Duration",
                    value=duration,
                    delta="Estimated"
                )
            
            with col_risk3:
                st.metric(
                    label="Confidence Level",
                    value=f"{confidence}%",
                    delta="Analysis Confidence"
                )
            
            st.markdown("---")
            
            # Risk Categories Analysis
            st.subheader("📊 Risk Categories Breakdown")
            
            # Extract risk-related keywords for categorization
            text_lower = extracted_text.lower()
            
            risk_categories = {
                "Technical Risk": {
                    "indicators": ["technical", "system", "software", "hardware", "integration", "compatibility", "bug", "error", "failure"],
                    "score": 0
                },
                "Financial Risk": {
                    "indicators": ["budget", "cost", "expense", "funding", "investment", "financial", "money", "price", "revenue"],
                    "score": 0
                },
                "Schedule Risk": {
                    "indicators": ["deadline", "delay", "timeline", "schedule", "milestone", "late", "overdue", "time"],
                    "score": 0
                },
                "Resource Risk": {
                    "indicators": ["resource", "staff", "team", "personnel", "capacity", "availability", "shortage", "skill"],
                    "score": 0
                },
                "Compliance Risk": {
                    "indicators": ["compliance", "regulatory", "legal", "policy", "standard", "requirement", "audit", "governance"],
                    "score": 0
                },
                "Operational Risk": {
                    "indicators": ["operational", "process", "workflow", "efficiency", "performance", "quality", "maintenance"],
                    "score": 0
                }
            }
            
            # Calculate scores for each category
            for category, data in risk_categories.items():
                count = sum(1 for word in data["indicators"] if word in text_lower)
                data["score"] = min(10, count * 2)  # Scale to 0-10
            
            # Display risk categories
            col_cat1, col_cat2 = st.columns(2)
            
            categories_list = list(risk_categories.items())
            
            with col_cat1:
                for category, data in categories_list[:3]:
                    score = data["score"]
                    level = "🟢 Low" if score <= 3 else "🟡 Medium" if score <= 6 else "🔴 High"
                    st.write(f"**{category}:** {level}")
                    st.progress(score / 10)
            
            with col_cat2:
                for category, data in categories_list[3:]:
                    score = data["score"]
                    level = "🟢 Low" if score <= 3 else "🟡 Medium" if score <= 6 else "🔴 High"
                    st.write(f"**{category}:** {level}")
                    st.progress(score / 10)
            
            st.markdown("---")
            
            # Risk Indicators Found
            st.subheader("⚠️ Risk Indicators Detected")
            
            high_risk_words = ['urgent', 'critical', 'risk', 'delay', 'issue', 'problem', 'challenge', 'concern', 'failure', 'crisis', 'threat', 'danger', 'warning']
            medium_risk_words = ['consider', 'review', 'assess', 'evaluate', 'potential', 'uncertain', 'unclear', 'possible', 'might', 'could']
            positive_words = ['complete', 'success', 'achieved', 'approved', 'confirmed', 'stable', 'secure', 'resolved', 'mitigated', 'controlled']
            
            found_high = [word for word in high_risk_words if word in text_lower]
            found_medium = [word for word in medium_risk_words if word in text_lower]
            found_positive = [word for word in positive_words if word in text_lower]
            
            col_ind1, col_ind2, col_ind3 = st.columns(3)
            
            with col_ind1:
                st.markdown("**🔴 High Risk Indicators**")
                if found_high:
                    for word in found_high[:5]:
                        st.write(f"• {word.capitalize()}")
                else:
                    st.write("None detected ✓")
            
            with col_ind2:
                st.markdown("**🟡 Medium Risk Indicators**")
                if found_medium:
                    for word in found_medium[:5]:
                        st.write(f"• {word.capitalize()}")
                else:
                    st.write("None detected ✓")
            
            with col_ind3:
                st.markdown("**🟢 Positive Indicators**")
                if found_positive:
                    for word in found_positive[:5]:
                        st.write(f"• {word.capitalize()}")
                else:
                    st.write("None detected")
            
            st.markdown("---")
            
            # Risk Mitigation Recommendations
            st.subheader("💡 Risk Mitigation Recommendations")
            
            recommendations = []
            
            if risk_score < 4:
                recommendations.append("⚠️ **High Priority:** Conduct immediate risk assessment meeting with stakeholders")
                recommendations.append("📋 Develop detailed contingency plans for identified risks")
                recommendations.append("👥 Consider allocating additional resources to risk mitigation")
            
            if any(cat["score"] > 6 for cat in risk_categories.values()):
                high_risk_cats = [cat for cat, data in risk_categories.items() if data["score"] > 6]
                for cat in high_risk_cats:
                    recommendations.append(f"🎯 Focus on reducing **{cat}** through targeted interventions")
            
            if "delay" in text_lower or "deadline" in text_lower:
                recommendations.append("⏰ Implement schedule monitoring and early warning systems")
            
            if "budget" in text_lower or "cost" in text_lower:
                recommendations.append("💰 Establish budget tracking and cost control measures")
            
            if len(recommendations) == 0:
                recommendations.append("✅ Risk levels appear manageable - maintain regular monitoring")
                recommendations.append("📊 Continue periodic risk assessments throughout project lifecycle")
                recommendations.append("📝 Document lessons learned for future risk management")
            
            for rec in recommendations:
                st.markdown(rec)
            
            st.markdown("---")
            
            # Risk Summary Table
            st.subheader("📋 Risk Summary Report")
            
            risk_summary_html = f"""
            <table class="styled-table">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Overall Risk Score</td>
                        <td>{risk_score}/10</td>
                        <td>{'🟢' if risk_score >= 7 else '🟡' if risk_score >= 4 else '🔴'} {risk_level}</td>
                    </tr>
                    <tr>
                        <td>High Risk Indicators</td>
                        <td>{len(found_high)}</td>
                        <td>{'🟢' if len(found_high) <= 1 else '🟡' if len(found_high) <= 3 else '🔴'}</td>
                    </tr>
                    <tr>
                        <td>Positive Indicators</td>
                        <td>{len(found_positive)}</td>
                        <td>{'🟢' if len(found_positive) >= 3 else '🟡' if len(found_positive) >= 1 else '🔴'}</td>
                    </tr>
                    <tr>
                        <td>Go/No-Go Decision</td>
                        <td>{verdict}</td>
                        <td>{confidence}% Confidence</td>
                    </tr>
                    <tr>
                        <td>Estimated Duration</td>
                        <td>{duration}</td>
                        <td>📅</td>
                    </tr>
                </tbody>
            </table>
            """
            st.markdown(risk_summary_html, unsafe_allow_html=True)
            
        with tab_translation:
            st.subheader(f"Translate to {target_lang}")
            
            # Get original file type
            file_type = uploaded_file.name.split('.')[-1].lower()
            
            # Translation mode selection
            translation_mode = st.radio(
                "Translation Mode",
                ["Preserve Original Formatting (Recommended)", "Create New Document", "Plain Text Only"],
                horizontal=True,
                help="'Preserve Formatting' keeps the original document structure and styling"
            )
            
            if st.button("🌐 Translate Document", type="primary"):
                original_name = uploaded_file.name.rsplit('.', 1)[0]
                
                if translation_mode == "Preserve Original Formatting (Recommended)":
                    # Translate in-place preserving formatting
                    if file_type == 'docx' and DOCX_SUPPORT:
                        with st.spinner(f'Translating DOCX to {target_lang} (preserving formatting)...'):
                            uploaded_file.seek(0)  # Reset file pointer
                            doc_buffer, error = translate_docx_inplace(uploaded_file, target_lang)
                        
                        if error:
                            st.error(error)
                        else:
                            st.success(f"✅ Document translated with original formatting preserved!")
                            st.download_button(
                                label="📥 Download Translated DOCX (Original Format)",
                                data=doc_buffer,
                                file_name=f"{original_name}_{target_lang.lower().replace(' ', '_')}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                    
                    elif file_type in ['pptx', 'ppt']:
                        with st.spinner(f'Translating PPTX to {target_lang} (preserving formatting)...'):
                            uploaded_file.seek(0)  # Reset file pointer
                            pptx_buffer, error = translate_pptx_inplace(uploaded_file, target_lang)
                        
                        if error:
                            st.error(error)
                        else:
                            st.success(f"✅ Presentation translated with original formatting preserved!")
                            st.download_button(
                                label="📥 Download Translated PPTX (Original Format)",
                                data=pptx_buffer,
                                file_name=f"{original_name}_{target_lang.lower().replace(' ', '_')}.pptx",
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                            )
                    
                    elif file_type == 'pdf':
                        st.warning("⚠️ PDF in-place translation not supported. Using 'Create New Document' mode instead.")
                        # Fall back to creating new document
                        with st.spinner(f'Translating to {target_lang}...'):
                            translated_text = translate_text(extracted_text, target_lang)
                        
                        if DOCX_SUPPORT:
                            doc_buffer = create_translated_docx(translated_text, target_lang, uploaded_file.name)
                            st.download_button(
                                label="📥 Download as Translated DOCX",
                                data=doc_buffer,
                                file_name=f"{original_name}_{target_lang.lower().replace(' ', '_')}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                        else:
                            st.download_button(
                                label="📥 Download as Text",
                                data=translated_text,
                                file_name=f"{original_name}_{target_lang.lower()}.txt",
                                mime="text/plain"
                            )
                    else:
                        st.error(f"Unsupported file type for in-place translation: {file_type}")
                
                elif translation_mode == "Create New Document":
                    with st.spinner(f'Translating to {target_lang}...'):
                        translated_text = translate_text(extracted_text, target_lang)
                    
                    st.text_area(
                        f"Translation Preview ({target_lang}):", 
                        translated_text[:2000] + ("..." if len(translated_text) > 2000 else ""), 
                        height=150
                    )
                    
                    # Offer both DOCX and PPTX options
                    col1, col2 = st.columns(2)
                    with col1:
                        if DOCX_SUPPORT:
                            doc_buffer = create_translated_docx(translated_text, target_lang, uploaded_file.name)
                            st.download_button(
                                label="📥 Download as DOCX",
                                data=doc_buffer,
                                file_name=f"{original_name}_{target_lang.lower().replace(' ', '_')}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                    with col2:
                        pptx_buffer = create_translated_pptx(translated_text, target_lang, uploaded_file.name)
                        st.download_button(
                            label="📥 Download as PPTX",
                            data=pptx_buffer,
                            file_name=f"{original_name}_{target_lang.lower().replace(' ', '_')}.pptx",
                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                        )
                    
                    st.success(f"✅ Translation complete! {len(translated_text.split())} words translated.")
                
                else:  # Plain Text Only
                    with st.spinner(f'Translating to {target_lang}...'):
                        translated_text = translate_text(extracted_text, target_lang)
                    
                    st.text_area(
                        f"Translation ({target_lang}):", 
                        translated_text, 
                        height=300
                    )
                    
                    st.download_button(
                        label="📥 Download Translation (TXT)",
                        data=translated_text,
                        file_name=f"{original_name}_{target_lang.lower().replace(' ', '_')}.txt",
                        mime="text/plain"
                    )
                    st.success(f"✅ Translation complete! {len(translated_text.split())} words translated.")
            else:
                st.info("Click the button above to translate the document content.")