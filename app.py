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

# Получаем ключ
if "GOOGLE_API_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    MY_API_KEY = "AIzaSy..." # Локальный ключ

def load_ai():
    try:
        genai.configure(api_key=MY_API_KEY)
        for m_name in ['gemini-1.5-flash', 'gemini-1.5-flash-001', 'gemini-pro']:
            try:
                return genai.GenerativeModel(m_name)
            except: continue
    except: pass
    return None

model = load_ai()

# --- 2. СПИСКИ ПРЕДМЕТОВ (ПО КАТЕГОРИЯМ) ---
SUBJECTS_DB = {
    "Языки и Литература": ["Русский язык", "Казахский язык", "Английский язык", "Русская литература", "Казахская литература"],
    "Мат / Ест / Инф": ["Математика", "Алгебра", "Геометрия", "Информатика", "Естествознание", "Физика", "Химия", "Биология", "География"],
    "Общество / История": ["Всемирная история", "История Казахстана", "Основы права", "Самопознание"],
    "Искусство / Технологии": ["Художественный труд", "Музыка", "Графика и проектирование"]
}

# --- 3. ОЧИСТКА ТЕКСТА ---
def clean_content(text):
    text = text.replace('**', '').replace('###', '').replace('##', '').replace('#', '').replace('*', '')
    stop_phrases = ["роль:", "задача:", "конечно", "вот ваш", "согласно госо", "тип материала:", "инструкция"]
    
    lines = text.split('\n')
    final_lines = []
    for line in lines:
        clean_line = line.strip()
        if not clean_line: continue
        if any(phrase in clean_line.lower() for phrase in stop_phrases) and len(clean_line) < 100:
            continue
        final_lines.append(clean_line)
    return final_lines

# --- 4. БЕЗОПАСНАЯ ГЕНЕРАЦИЯ ---
def generate_safe(prompt):
    for i in range(3):
        try:
            return model.generate_content(prompt)
        except exceptions.ResourceExhausted:
            time.sleep(5)
        except: time.sleep(1)
    return None

# --- 5. WORD ЭКСПОРТ ---
def save_to_docx(lines, title, subj, grade, teacher, max_score, is_sor, student_name=""):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)

    header_text = "БЖБ (СОР) / ТЖБ (СОЧ)" if is_sor else "ЖҰМЫС ПАРАҒЫ / РАБОЧИЙ ЛИСТ"
    
    table = doc.add_table(rows=2, cols=2)
    table.columns[0].width = Inches(4.5)
    
    table.cell(0, 0).text = f"Оқушы / Ученик: {student_name if student_name else '____________________'}"
    table.cell(1, 0).text = f"Пән / Предмет: {subj} | Сынып / Класс: {grade}"
    
    c01 = table.cell(0, 1)
    c01.text = "Күні / Дата: «___» ________ 202_ г."
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
        if any(line.lower().startswith(s) for s in ["задание", "тапсырма", "1.", "2.", "3.", "текст"]):
            p.bold = True
            if "текст" not in line.lower() and "критерий" not in line.lower() and is_sor:
                doc.add_paragraph("Жауабы / Ответ: " + "_"*60)

    doc.add_paragraph("\n" + "_"*50)
    doc.add_paragraph(f"Мұғалім: {teacher} ____________ (қолы)").alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    buf = BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- 6. ИНТЕРФЕЙС ---
with st.sidebar:
    st.title("🇰🇿 Методист PRO")
    t_name = st.text_input("ФИО Учителя:", value="Учитель")
    
    st.divider()
    # ГЛАВНАЯ НАСТРОЙКА ЯЗЫКА
    class_lang = st.radio("Язык обучения класса:", ["Русский", "Казахский"])
    
    st.divider()
    st.subheader("Тип материала:")
    opt_work = st.checkbox("Рабочий лист", value=True)
    opt_sor = st.checkbox("СОР / СОЧ (Контроль)")
    
    st.subheader("Компетенции:")
    opt_func = st.checkbox("Функц. грамотность (МОДО)", value=True)
    opt_pisa = st.checkbox("PISA / PIRLS")
    opt_audit = st.checkbox("Аудирование")

# Вкладки
tab_main, tab_reserve = st.tabs(["📚 ГЕНЕРАТОР", "♿ ИНКЛЮЗИЯ"])

with tab_main:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        # Выбор категории и предмета
        cat = st.selectbox("Категория:", list(SUBJECTS_DB.keys()))
        u_subj = st.selectbox("Предмет:", SUBJECTS_DB[cat])
    with c2:
        u_grade = st.selectbox("Класс:", [str(i) for i in range(1, 12)])
        u_score = st.number_input("Макс. балл:", 1, 80, 10)
    with c3:
        u_topic = st.text_input("Тема урока:")
    
    u_goals = st.text_area("Цели обучения (ЦО) из КТП:", height=100, placeholder="Например: 5.1.2.1...")

    if st.button("🚀 Создать материал"):
        if model and u_topic and u_goals:
            # ЛОГИКА ОПРЕДЕЛЕНИЯ Я1 / Я2
            lang_instruction = ""
            is_l2 = False
            
            if "Русский язык" in u_subj:
                if class_lang == "Казахский":
                    lang_instruction = "ЭТО РУССКИЙ ЯЗЫК КАК ВТОРОЙ (Я2) для казахских классов."
                    is_l2 = True
                else:
                    lang_instruction = "ЭТО РУССКИЙ ЯЗЫК КАК РОДНОЙ (Я1)."
            elif "Казахский язык" in u_subj:
                if class_lang == "Русский":
                    lang_instruction = "ЭТО КАЗАХСКИЙ ЯЗЫК КАК ВТОРОЙ (Т2) для русских классов."
                    is_l2 = True
                else:
                    lang_instruction = "ЭТО КАЗАХСКИЙ ЯЗЫК КАК РОДНОЙ (Т1)."
            else:
                lang_instruction = f"Язык обучения: {class_lang}."

            # Дополнительные настройки для Л2 (Второй язык)
            l2_prompt = ""
            if is_l2:
                l2_prompt = """
                МЕТОДИКА Л2 (Второй язык):
                - Используй коммуникативный подход.
                - Лексика должна быть доступной, фразы клишированными.
                - Грамматика дается через примеры и диалоги.
                - Избегай слишком сложных научных терминов, если они не в теме.
                """

            reqs = []
            if opt_work: reqs.append("практические задания")
            if opt_sor: reqs.append("суммативное оценивание (СОР)")
            if opt_func: reqs.append("задания на функциональную грамотность")
            if opt_pisa: reqs.append("PISA (критическое мышление)")
            if opt_audit: reqs.append("аудирование (скрипт + вопросы)")

            prompt = f"""
            Роль: Методист Казахстана. Предмет: {u_subj}. Класс: {u_grade}.
            Тема: {u_topic}. Цели (ЦО): {u_goals}.
            ЯЗЫКОВОЙ КОНТЕКСТ: {lang_instruction}
            {l2_prompt}
            
            ВКЛЮЧИТЬ: {', '.join(reqs)}.
            
            ТРЕБОВАНИЯ ГОСО:
            1. Задания СТРОГО проверяют указанные ЦО.
            2. Если это СОР - сумма баллов ровно {u_score}.
            3. НИКАКОГО Markdown (звездочек). Только чистый текст.
            4. Таблица дескрипторов в конце (1 шаг = 1 балл).
            """
            
            with st.spinner("Анализ методики преподавания..."):
                res = generate_safe(prompt)
                if res:
                    clean = clean_content(res.text)
                    st.success("Готово!")
                    docx = save_to_docx(clean, u_topic, u_subj, u_grade, t_name, u_score, opt_sor)
                    st.download_button("💾 СКАЧАТЬ WORD", docx, file_name=f"{u_subj}_{u_topic}.docx")
        else:
            st.warning("Заполните тему и цели!")

with tab_reserve:
    st.info("Адаптация для ООП (Особые образовательные потребности)")
    r_name = st.text_input("Имя ученика:")
    r_score = st.number_input("Балл (Резерв):", 1, 50, 5)
    
    if st.button("🪄 Адаптировать"):
        if u_goals:
            prompt = f"""
            Коррекционный педагог. Адаптируй тему '{u_topic}' для ученика {r_name}.
            Предмет: {u_subj}. Язык класса: {class_lang}.
            Упрости задания до уровня 'Узнавание' и 'Понимание'.
            Используй тесты и соединения. Макс балл: {r_score}.
            """
            with st.spinner("Адаптация..."):
                res = generate_safe(prompt)
                if res:
                    clean = clean_content(res.text)
                    docx = save_to_docx(clean, f"Резерв: {u_topic}", u_subj, u_grade, t_name, r_score, False, r_name)
                    st.download_button("💾 СКАЧАТЬ WORD (РЕЗЕРВ)", docx, file_name=f"Reserve_{r_name}.docx")
