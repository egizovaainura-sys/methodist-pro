import streamlit as st
import google.generativeai as genai
import time
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. НАСТРОЙКИ СИСТЕМЫ ---
st.set_page_config(page_title="Методист PRO: Перезагрузка", layout="wide")

# Инициализация памяти (чтобы данные не пропадали при скачивании)
if 'doc_ready' not in st.session_state:
    st.session_state.doc_ready = False
if 'generated_text' not in st.session_state:
    st.session_state.generated_text = ""
if 'docx_data' not in st.session_state:
    st.session_state.docx_data = None

# ПРОВЕРКА КЛЮЧА
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("🚨 ОШИБКА: API КЛЮЧ НЕ НАЙДЕН В НАСТРОЙКАХ (SECRETS)!")
    st.stop()

# --- 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def clean_content(text):
    text = text.replace('**', '').replace('###', '').replace('##', '').replace('#', '').replace('*', '')
    lines = text.split('\n')
    return [l.strip() for l in lines if l.strip()]

def save_to_docx(lines, title, subj, grade, teacher, max_score):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)

    # Шапка
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = f"Ученик: ____________________"
    table.cell(1, 0).text = f"Пән: {subj} | Класс: {grade}"
    table.cell(0, 1).text = f"Дата: ________"
    table.cell(1, 1).text = f"Балл: ___ / {max_score}"

    doc.add_paragraph()
    h = doc.add_heading(title.upper(), 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in h.runs:
        run.font.name = 'Times New Roman'; run.font.color.rgb = RGBColor(0,0,0); run.font.size = Pt(14); run.bold = True

    for line in lines:
        if line.startswith('|'):
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells and "---" not in line:
                tbl = doc.add_table(rows=1, cols=len(cells))
                tbl.style = 'Table Grid'
                for j, val in enumerate(cells): tbl.cell(0, j).text = val
            continue
        p = doc.add_paragraph(line)
        if any(line.lower().startswith(s) for s in ["задание", "тапсырма", "1.", "вопрос"]):
            p.bold = True

    buf = BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- 3. ИНТЕРФЕЙС ---
st.title("🇰🇿 Методист PRO (Исправленная версия)")

with st.sidebar:
    t_name = st.text_input("👤 ФИО Учителя:", value="Педагог")
    c_lang = st.radio("Язык обучения:", ["Русский", "Казахский"])
    st.divider()
    opt_low_mot = st.checkbox("🔥 Слабая мотивация")
    opt_sor = st.checkbox("СОР / СОЧ")
    opt_audit = st.checkbox("Аудирование")

col1, col2 = st.columns(2)
with col1:
    u_subj = st.text_input("Предмет:", value="Русский язык")
    u_grade = st.selectbox("Класс:", [str(i) for i in range(1, 12)])
with col2:
    u_topic = st.text_input("Тема урока (ОБЯЗАТЕЛЬНО):")
    u_score = st.number_input("Макс. балл:", 1, 50, 10)

u_goals = st.text_area("Цели обучения (ЦО):")

# КНОПКА ГЕНЕРАЦИИ
if st.button("🚀 СГЕНЕРИРОВАТЬ ЗАДАНИЯ", use_container_width=True):
    if not u_topic:
        st.warning("⚠️ Сначала напишите тему урока!")
    else:
        with st.spinner("Связь с искусственным интеллектом... подождите..."):
            try:
                prompt = f"""Методист РК. ПРЕДМЕТ: {u_subj}. ЯЗЫК: {c_lang}. КЛАСС: {u_grade}. ТЕМА: {u_topic}. ЦО: {u_goals}. 
                Сделай {'СОР' if opt_sor else 'Рабочий лист'}. 
                {'Адаптируй для слабомотивированного ученика.' if opt_low_mot else ''}
                {'Включи аудирование.' if opt_audit else ''}
                БЕЗ Markdown (звездочек). Баллы: {u_score}. В конце таблица критериев."""
                
                response = model.generate_content(prompt)
                
                if response and response.text:
                    st.session_state.generated_text = response.text
                    clean_lines = clean_content(response.text)
                    st.session_state.docx_data = save_to_docx(clean_lines, u_topic, u_subj, u_grade, t_name, u_score)
                    st.session_state.doc_ready = True
                else:
                    st.error("ИИ не ответил. Попробуйте изменить тему.")
            except Exception as e:
                st.error(f"Произошла ошибка: {str(e)}")

# ВЫВОД РЕЗУЛЬТАТА И КНОПКА СКАЧИВАНИЯ
if st.session_state.doc_ready:
    st.success("✅ Материал успешно создан!")
    
    st.download_button(
        label="📥 СКАЧАТЬ ВОРД (WORD .docx)",
        data=st.session_state.docx_data,
        file_name=f"{u_subj}_{u_topic}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True
    )
    
    with st.expander("👀 Предварительный просмотр текста"):
        st.write(st.session_state.generated_text)
