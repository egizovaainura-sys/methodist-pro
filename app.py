import streamlit as st
import google.generativeai as genai
import time
import re
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from google.api_core import exceptions

# --- 1. НАСТРОЙКИ СИСТЕМЫ ---
st.set_page_config(page_title="Методист PRO: Адаптация", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    MY_API_KEY = "AIzaSy..."

def load_ai():
    try:
        genai.configure(api_key=MY_API_KEY)
        for m_name in ['gemini-1.5-flash', 'gemini-pro']:
            try: return genai.GenerativeModel(m_name)
            except: continue
    except: pass
    return None

model = load_ai()

# --- 2. БАЗА ПРЕДМЕТОВ ---
SUBJECTS_DB = {
    "Языки и Литература": ["Русский язык (Я1)", "Русский язык (Я2)", "Қазақ тілі (Т1)", "Қазақ тілі (Т2)", "Английский язык", "Литература"],
    "Мат / Ест / Инф": ["Математика", "Алгебра", "Геометрия", "Информатика", "Физика", "Химия", "Биология", "География"],
    "Начальная школа": ["Математика (Нач)", "Познание мира", "Естествознание (Нач)", "Ана тілі", "Көркем еңбек"]
}

# --- 3. ОЧИСТКА ТЕКСТА ---
def clean_content(text):
    text = text.replace('**', '').replace('###', '').replace('##', '').replace('#', '').replace('*', '')
    stop_phrases = ["роль:", "задача:", "конечно", "вот ваш", "тип материала:", "инструкция"]
    lines = text.split('\n')
    final_lines = []
    for line in lines:
        clean_line = line.strip()
        if not clean_line or any(p in clean_line.lower() for p in stop_phrases): continue
        final_lines.append(clean_line)
    return final_lines

# --- 4. WORD ЭКСПОРТ ---
def save_to_docx(lines, title, subj, grade, teacher, max_score, doc_type, student_name="", variant=1, is_low_mot=False):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)

    # Шапка
    h_text = "БЖБ / СОЧ" if doc_type == "SOR" else ("ТЕСТ" if doc_type == "TEST" else "ЖҰМЫС ПАРАҒЫ")
    if is_low_mot: h_text += " (Адаптивті)"

    table = doc.add_table(rows=2, cols=2)
    table.columns[0].width = Inches(4.5)
    table.cell(0, 0).text = f"Оқушы / Ученик: {student_name if student_name else '____________________'}"
    table.cell(1, 0).text = f"Пән: {subj} | Сынып: {grade}"
    table.cell(0, 1).text = f"Дата: ________ | Вар: {variant}"
    table.cell(1, 1).text = f"Макс. балл: {max_score}"

    doc.add_paragraph()
    h = doc.add_heading(title.upper(), 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in h.runs:
        run.font.name = 'Times New Roman'; run.font.color.rgb = RGBColor(0,0,0); run.font.size = Pt(14); run.bold = True

    for line in lines:
        if line.startswith('|') and "---" not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                tbl = doc.add_table(rows=1, cols=len(cells)); tbl.style = 'Table Grid'
                for j, val in enumerate(cells): tbl.cell(0, j).text = val
            continue
        p = doc.add_paragraph(line)
        if any(line.lower().startswith(s) for s in ["задание", "тапсырма", "1.", "вопрос"]):
            p.bold = True
            if doc_type == "SOR": doc.add_paragraph("Жауабы: " + "_"*50)

    if is_low_mot:
        doc.add_paragraph("\n⭐ Рефлексия: Маған тапсырма... (Оңай/Қиын/Қызықты) _________")

    doc.add_paragraph("\n" + "_"*40)
    doc.add_paragraph(f"Мұғалім: {teacher} ____________").alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    buf = BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- 5. ГЕНЕРАЦИЯ ---
def generate_safe(prompt):
    for i in range(3):
        try: return model.generate_content(prompt)
        except: time.sleep(2)
    return None

# --- 6. ИНТЕРФЕЙС ---
with st.sidebar:
    st.title("🇰🇿 Методист PRO")
    t_name = st.text_input("👤 ФИО Учителя:", value="Педагог")
    class_lang = st.radio("Язык обучения:", ["Русский", "Казахский"])
    st.divider()
    
    st.subheader("Настройки адаптации:")
    opt_low_mot = st.checkbox("🔥 Слабая мотивация", help="ИИ сделает задания интереснее, добавит подсказки и упростит вход в тему.")
    
    st.divider()
    st.subheader("Тип материала:")
    opt_work = st.checkbox("Рабочий лист", value=True)
    opt_sor = st.checkbox("СОР / СОЧ")
    opt_audit = st.checkbox("Аудирование")
    opt_func = st.checkbox("МОДО")

tab1, tab2, tab3 = st.tabs(["📚 ЗАДАНИЯ", "📝 ТЕСТЫ", "♿ ИНКЛЮЗИЯ"])

# ВКЛАДКА 1
with tab1:
    c1, c2, c3 = st.columns(3)
    with c1:
        cat = st.selectbox("Категория:", list(SUBJECTS_DB.keys()), key="c1")
        u_subj = st.selectbox("Предмет:", SUBJECTS_DB[cat], key="s1")
    with c2:
        u_grade = st.selectbox("Класс:", [str(i) for i in range(1, 12)], key="g1")
        u_score = st.number_input("Макс. балл:", 1, 80, 10, key="sc1")
    with c3:
        u_var = st.number_input("Вариант:", 1, 4, 1, key="v1")
        
    u_topic = st.text_input("Тема урока:", key="t1")
    u_goals = st.text_area("Цели обучения (ЦО):", key="gl1")
    u_wish = st.text_area("✍️ Особые пожелания:", key="w1")

    if st.button("🚀 СОЗДАТЬ И СКАЧАТЬ ВОРД"):
        if model and u_topic:
            with st.spinner("Адаптируем задания..."):
                mot_prompt = ""
                if opt_low_mot:
                    mot_prompt = """
                    МЕТОДИКА ДЛЯ СЛАБОМОТИВИРОВАННЫХ:
                    - Используй 'эффект успеха': начни с очень простого.
                    - Добавляй короткие интересные факты по теме.
                    - Давай краткие подсказки (алгоритмы) к сложным заданиям.
                    - Инструкции должны быть короткими и дружелюбными.
                    """

                prompt = f"""Методист РК. Предмет: {u_subj}. Язык: {class_lang}. Класс: {u_grade}. Тема: {u_topic}. ЦО: {u_goals}. 
                {mot_prompt}
                Тип: {'СОР' if opt_sor else 'Рабочий лист'}. Пожелания: {u_wish}.
                Включить {'аудирование' if opt_audit else ''} и {'МОДО' if opt_func else ''}. 
                БЕЗ Markdown. Баллы: {u_score}. В конце таблица критериев."""
                
                res = generate_safe(prompt)
                if res:
                    clean = clean_content(res.text)
                    docx = save_to_docx(clean, u_topic, u_subj, u_grade, t_name, u_score, "SOR" if opt_sor else "WORK", variant=u_var, is_low_mot=opt_low_mot)
                    st.download_button("📥 СКАЧАТЬ WORD (.docx)", docx, file_name=f"{u_subj}_{u_topic}.docx", use_container_width=True)

# ВКЛАДКА 2: ТЕСТЫ
with tab2:
    ts_count = st.slider("Количество вопросов:", 5, 30, 10)
    if st.button("📝 СФОРМИРОВАТЬ ТЕСТ В ВОРД"):
        if u_topic:
            prompt = f"Создай тест. Предмет: {u_subj}. Тема: {u_topic}. Вопросов: {ts_count}. Язык: {class_lang}. {'Адаптируй для слабомотивированных' if opt_low_mot else ''}. БЕЗ Markdown. В конце ответы."
            res = generate_safe(prompt)
            if res:
                clean = clean_content(res.text)
                docx = save_to_docx(clean, f"Тест: {u_topic}", u_subj, u_grade, t_name, ts_count, "TEST", is_low_mot=opt_low_mot)
                st.download_button("📥 СКАЧАТЬ ТЕСТ (.docx)", docx, file_name=f"Test_{u_topic}.docx", use_container_width=True)

# ВКЛАДКА 3: ИНКЛЮЗИЯ (ООП)
with tab3:
    r_name = st.text_input("Имя ученика:", key="rn")
    r_type = st.radio("Тип адаптации:", ["Слабая мотивация", "ООП (Трудности в обучении)", "ЗПР/Нарушения"])
    if st.button("🪄 ПОДГОТОВИТЬ ПЕРСОНАЛЬНО"):
        if u_topic and r_name:
            prompt = f"Адаптируй тему {u_topic} для ученика {r_name}. Тип адаптации: {r_type}. Язык: {class_lang}. Упрости, добавь опоры. БЕЗ Markdown."
            res = generate_safe(prompt)
            if res:
                clean = clean_content(res.text)
                docx = save_to_docx(clean, "Персональный лист", u_subj, u_grade, t_name, 5, "WORK", student_name=r_name, is_low_mot=(r_type=="Слабая мотивация"))
                st.download_button(f"📥 СКАЧАТЬ ДЛЯ {r_name.upper()}", docx, file_name=f"Personal_{r_name}.docx", use_container_width=True)
