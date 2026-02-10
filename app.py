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
st.set_page_config(page_title="Методист PRO: ГОСО", layout="wide")

# Загрузка API ключа из Secrets
if "GOOGLE_API_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    MY_API_KEY = "AIzaSy..." # Для тестов

def load_ai():
    try:
        genai.configure(api_key=MY_API_KEY)
        for m_name in ['gemini-1.5-flash', 'gemini-pro']:
            try: return genai.GenerativeModel(m_name)
            except: continue
    except: pass
    return None

model = load_ai()

# --- 2. БАЗА ПРЕДМЕТОВ (Я1/Я2) ---
SUBJECTS_DB = {
    "Языки и Литература": [
        "Русский язык (Я1 - для русских классов)", 
        "Русский язык (Я2 - для казахских классов)", 
        "Қазақ тілі (Т1 - қазақ сыныптары үшін)", 
        "Қазақ тілі (Т2 - орыс сыныптары үшін)", 
        "Английский язык", "Литературное чтение", "Русская литература", "Қазақ әдебиеті"
    ],
    "Мат / Ест / Инф": ["Математика", "Алгебра", "Геометрия", "Информатика", "Естествознание", "Физика", "Химия", "Биология", "География"],
    "Общество / История": ["Всемирная история", "История Казахстана", "Основы права", "Глобальные компетенции"],
    "Начальная школа": ["Математика (Нач)", "Познание мира", "Естествознание (Нач)", "Ана тілі", "Енбек"]
}

# --- 3. ОЧИСТКА ТЕКСТА ---
def clean_content(text):
    text = text.replace('**', '').replace('###', '').replace('##', '').replace('#', '').replace('*', '')
    stop_phrases = ["роль:", "задача:", "конечно", "вот ваш", "тип материала:", "инструкция"]
    lines = text.split('\n')
    final_lines = []
    for line in lines:
        clean_line = line.strip()
        if not clean_line: continue
        if any(phrase in clean_line.lower() for phrase in stop_phrases) and len(clean_line) < 100: continue
        final_lines.append(clean_line)
    return final_lines

# --- 4. WORD ЭКСПОРТ (ГОТОВ К ПЕЧАТИ) ---
def save_to_docx(lines, title, subj, grade, teacher, max_score, doc_type, student_name="", variant=1):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)

    # Шапка документа
    if doc_type == "SOR": header_text = "БЖБ (СОР) / ТЖБ (СОЧ)"
    elif doc_type == "TEST": header_text = f"ТЕСТ (Вариант {variant})"
    else: header_text = "ЖҰМЫС ПАРАҒЫ / РАБОЧИЙ ЛИСТ"
    
    table = doc.add_table(rows=2, cols=2)
    table.columns[0].width = Inches(4.5)
    table.cell(0, 0).text = f"Оқушы / Ученик: {student_name if student_name else '____________________'}"
    table.cell(1, 0).text = f"Пән: {subj} | Сынып: {grade}"
    
    c01 = table.cell(0, 1)
    c01.text = "Күні: «___» ________ 202_ г."
    c01.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    c11 = table.cell(1, 1)
    c11.text = f"{header_text}\nБалл: ___ / {max_score}"
    c11.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph()
    h = doc.add_heading(title.upper(), 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in h.runs:
        run.font.name = 'Times New Roman'; run.font.color.rgb = RGBColor(0,0,0); run.font.size = Pt(14); run.bold = True

    for line in lines:
        if line.startswith('|') and "---" not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                tbl = doc.add_table(rows=1, cols=len(cells))
                tbl.style = 'Table Grid'
                for j, val in enumerate(cells): tbl.cell(0, j).text = val
            continue
            
        p = doc.add_paragraph(line)
        if any(line.lower().startswith(s) for s in ["задание", "тапсырма", "1.", "2.", "3.", "текст", "вопрос"]):
            p.bold = True
            if doc_type == "SOR" and "текст" not in line.lower() and "критерий" not in line.lower():
                doc.add_paragraph("Жауабы / Ответ: " + "_"*60)

    doc.add_paragraph("\n" + "_"*50)
    doc.add_paragraph(f"Мұғалім: {teacher} ____________").alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    buf = BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- 5. ГЕНЕРАЦИЯ (С ЗАЩИТОЙ) ---
def generate_safe(prompt):
    for i in range(3):
        try: return model.generate_content(prompt)
        except: time.sleep(2)
    return None

# --- 6. ИНТЕРФЕЙС STREAMLIT ---
with st.sidebar:
    st.title("🇰🇿 Методист PRO")
    t_name = st.text_input("ФИО Учителя:", value="Учитель")
    st.divider()
    class_lang = st.radio("Язык обучения класса:", ["Русский", "Казахский"])
    st.divider()
    st.subheader("Тип материала:")
    opt_work = st.checkbox("Рабочий лист", value=True)
    opt_sor = st.checkbox("СОР / СОЧ")
    st.subheader("Дополнительно:")
    opt_func = st.checkbox("МОДО")
    opt_audit = st.checkbox("Аудирование (Скрипт)")

tab_main, tab_test, tab_reserve = st.tabs(["📚 ЗАДАНИЯ", "📝 ТЕСТЫ", "♿ ИНКЛЮЗИЯ"])

# === ВКЛАДКА 1: ЗАДАНИЯ ===
with tab_main:
    c1, c2, c3 = st.columns(3)
    with c1:
        cat = st.selectbox("Категория:", list(SUBJECTS_DB.keys()), key="cat1")
        u_subj = st.selectbox("Предмет:", SUBJECTS_DB[cat], key="subj1")
    with c2:
        u_grade = st.selectbox("Класс:", [str(i) for i in range(1, 12)], key="gr1")
        u_score = st.number_input("Макс. балл:", 1, 80, 10)
    with c3:
        u_variant = st.number_input("Вариант:", 1, 4, 1)
        
    u_topic = st.text_input("Тема урока:")
    u_goals = st.text_area("Цели обучения (ЦО):", placeholder="Например: 5.1.2.1...")
    u_wishes = st.text_area("✍️ Особые пожелания (учет ИИ):")

    if st.button("🚀 Создать задания в Word"):
        if model and u_topic:
            reqs = []
            if opt_func: reqs.append("задания МОДО")
            if opt_audit: reqs.append("скрипт аудирования и 3 вопроса")
            
            prompt = f"""Методист Казахстана. Предмет: {u_subj}. Класс: {u_grade}. Язык обучения: {class_lang}.
            Тема: {u_topic}. ЦО: {u_goals}. Вариант: {u_variant}.
            Тип: {'СОР' if opt_sor else 'Рабочий лист'}. Пожелания: {u_wishes}.
            Включить: {', '.join(reqs) if reqs else 'стандартные задания'}.
            БЕЗ Markdown. Сумма баллов: {u_score}. В конце таблица критериев."""
            
            with st.spinner("Генерация..."):
                res = generate_safe(prompt)
                if res:
                    clean = clean_content(res.text)
                    docx = save_to_docx(clean, u_topic, u_subj, u_grade, t_name, u_score, "SOR" if opt_sor else "WORK", variant=u_variant)
                    st.download_button("💾 СКАЧАТЬ WORD", docx, file_name=f"{u_topic}.docx")

# === ВКЛАДКА 2: ТЕСТЫ ===
with tab_test:
    st.subheader("Конструктор тестов")
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        t_cat = st.selectbox("Категория:", list(SUBJECTS_DB.keys()), key="tcat")
        t_subj = st.selectbox("Предмет:", SUBJECTS_DB[t_cat], key="tsub")
    with tc2:
        t_count = st.slider("Количество вопросов:", 5, 30, 10)
        t_grade = st.selectbox("Класс:", [str(i) for i in range(1, 12)], key="tgr")
    with tc3:
        t_opts = st.selectbox("Вариантов ответа:", [3, 4, 5], index=1)
        t_var = st.number_input("Вариант теста:", 1, 10, 1)

    t_topic = st.text_input("Тема теста:")
    t_wishes = st.text_area("Пожелания к тесту (напр. 'только тесты с одним ответом'):")

    if st.button("📝 Создать ТЕСТ в Word"):
        if t_topic:
            prompt_test = f"Создай тест. Язык: {class_lang}. Предмет: {t_subj}. Тема: {t_topic}. Вопросов: {t_count}. Вариантов: {t_opts}. Пожелания: {t_wishes}. БЕЗ Markdown. В конце ключи ответов."
            with st.spinner("Составляем тест..."):
                res = generate_safe(prompt_test)
                if res:
                    clean = clean_content(res.text)
                    docx = save_to_docx(clean, f"Тест: {t_topic}", t_subj, t_grade, t_name, t_count, "TEST", variant=t_var)
                    st.download_button("💾 СКАЧАТЬ ТЕСТ", docx, file_name=f"Test_{t_topic}.docx")

# === ВКЛАДКА 3: ИНКЛЮЗИЯ ===
with tab_reserve:
    st.info("Адаптация для учеников с ООП")
    r_name = st.text_input("Имя ученика:")
    r_wish = st.text_area("Диагноз/Пожелания (напр. 'упростить текст, крупный шрифт'):")
    
    if st.button("🪄 Адаптировать"):
        if u_topic and r_name:
            prompt = f"Адаптируй тему {u_topic} ({u_subj}) для ученика {r_name} с ООП. Упрости задания. Пожелания: {r_wish}. БЕЗ Markdown."
            with st.spinner("Адаптация..."):
                res = generate_safe(prompt)
                if res:
                    clean = clean_content(res.text)
                    docx = save_to_docx(clean, "Адаптированный материал", u_subj, u_grade, t_name, 5, "WORK", student_name=r_name)
                    st.download_button("💾 СКАЧАТЬ ДЛЯ УЧЕНИКА", docx, file_name=f"Inclusive_{r_name}.docx")
