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
st.set_page_config(page_title="Методист PRO: PISA/PIRLS", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    MY_API_KEY = "AIzaSy..."

def load_ai():
    try:
        genai.configure(api_key=MY_API_KEY)
        for m_name in ['gemini-1.5-flash', 'gemini-1.5-flash-001', 'gemini-pro']:
            try: return genai.GenerativeModel(m_name)
            except: continue
    except: pass
    return None

model = load_ai()

# --- 2. БАЗА ПРЕДМЕТОВ ---
SUBJECTS_DB = {
    "Языки и Литература": [
        "Русский язык (Я1 - для русских классов)", 
        "Русский язык (Я2 - для казахских классов)", 
        "Қазақ тілі (Т1 - қазақ сыныптары үшін)", 
        "Қазақ тілі (Т2 - орыс сыныптары үшін)", 
        "Английский язык", "Литературное чтение"
    ],
    "Мат / Ест / Инф": ["Математика", "Алгебра", "Геометрия", "Информатика", "Естествознание", "Физика", "Химия", "Биология", "География"],
    "Общество / История": ["Всемирная история", "История Казахстана", "Основы права"],
    "Начальная школа": ["Математика (Нач)", "Познание мира", "Естествознание (Нач)"]
}

# --- 3. ОЧИСТКА ---
def clean_content(text):
    text = text.replace('**', '').replace('###', '').replace('##', '').replace('#', '').replace('*', '')
    stop_phrases = ["роль:", "задача:", "конечно", "вот ваш", "согласно госо", "тип материала:", "инструкция"]
    lines = text.split('\n')
    final_lines = []
    for line in lines:
        clean_line = line.strip()
        if not clean_line: continue
        if any(phrase in clean_line.lower() for phrase in stop_phrases) and len(clean_line) < 100: continue
        final_lines.append(clean_line)
    return final_lines

# --- 4. ГЕНЕРАЦИЯ ---
def generate_safe(prompt):
    for i in range(3):
        try: return model.generate_content(prompt)
        except: time.sleep(2)
    return None

# --- 5. WORD ЭКСПОРТ ---
def save_to_docx(lines, title, subj, grade, teacher, max_score, doc_type, student_name="", variant=1):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)

    # Заголовок
    if doc_type == "SOR": header_text = "БЖБ (СОР) / ТЖБ (СОЧ)"
    elif doc_type == "TEST": header_text = f"ТЕСТ (Вар. {variant})"
    elif doc_type == "PISA": header_text = "PISA / TIMSS ЗАДАНИЯ"
    elif doc_type == "PIRLS": header_text = "PIRLS (Оқу сауаттылығы)"
    else: header_text = "ЖҰМЫС ПАРАҒЫ / РАБОЧИЙ ЛИСТ"
    
    table = doc.add_table(rows=2, cols=2)
    table.columns[0].width = Inches(4.5)
    
    table.cell(0, 0).text = f"Оқушы / Ученик: {student_name if student_name else '____________________'}"
    table.cell(1, 0).text = f"Пән / Предмет: {subj} | Сынып: {grade}"
    
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
        if any(line.lower().startswith(s) for s in ["задание", "тапсырма", "1.", "2.", "3.", "текст", "вопрос"]):
            p.bold = True
            if doc_type == "SOR" and "текст" not in line.lower():
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
    
    class_lang = st.radio("Язык обучения класса:", ["Русский", "Казахский"])
    
    st.divider()
    st.subheader("Тип материала:")
    opt_work = st.checkbox("Рабочий лист (Практика)", value=True)
    opt_sor = st.checkbox("СОР / СОЧ (Контроль)")
    
    st.subheader("Международные стандарты:")
    opt_pisa = st.checkbox("PISA (Функц. грамотность)", help="Акцент на применение знаний в жизни, диаграммы, критическое мышление.")
    opt_pirls = st.checkbox("PIRLS (Чтение и понимание)", help="Работа с текстом: поиск информации, интерпретация, оценка.")
    opt_timss = st.checkbox("TIMSS (Мат. и Естествознание)", help="Академические знания + применение.")
    
    st.subheader("Другое:")
    opt_func = st.checkbox("МОДО (Нац. мониторинг)")
    opt_audit = st.checkbox("Аудирование")

tab_main, tab_test, tab_reserve = st.tabs(["📚 ЗАДАНИЯ", "📝 ТЕСТЫ", "♿ ИНКЛЮЗИЯ"])

# === ВКЛАДКА 1: ЗАДАНИЯ ===
with tab_main:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        cat = st.selectbox("Категория:", list(SUBJECTS_DB.keys()))
        u_subj = st.selectbox("Предмет:", SUBJECTS_DB[cat])
    with c2:
        u_grade = st.selectbox("Класс:", [str(i) for i in range(1, 12)])
        u_score = st.number_input("Макс. балл:", 1, 80, 10)
    with c3:
        u_variant = st.number_input("Вариант:", 1, 4, 1)
        
    u_topic = st.text_input("Тема урока:")
    u_goals = st.text_area("Цели обучения (ЦО):", height=70, placeholder="Например: 5.1.2.1...")
    u_wishes = st.text_area("✍️ Особые пожелания педагога:", placeholder="Например: включить текст про Астану")

    if st.button("🚀 Создать материал"):
        if model and u_topic:
            # Логика Языков
            lang_instr = f"Язык материала: {class_lang}."
            if "Я2" in u_subj or "Т2" in u_subj:
                lang_instr += " Это ВТОРОЙ язык (L2). Используй простую лексику, коммуникативный подход."
            
            # Логика PISA/PIRLS
            intl_st = []
            if opt_pisa: intl_st.append("формат PISA (ситуационные задачи, графики, критическое мышление)")
            if opt_pirls: intl_st.append("формат PIRLS (глубокий анализ текста: нахождение фактов, интерпретация, рефлексия)")
            if opt_timss: intl_st.append("формат TIMSS (знание терминов + применение формул)")
            if opt_func: intl_st.append("задания МОДО (функциональная грамотность)")
            
            intl_prompt = ""
            if intl_st:
                intl_prompt = f"ВКЛЮЧИТЬ МЕЖДУНАРОДНЫЕ СТАНДАРТЫ: {', '.join(intl_st)}."

            prompt = f"""
            Роль: Методист Казахстана. Предмет: {u_subj}. Класс: {u_grade}.
            Тема: {u_topic}. ЦЕЛИ: {u_goals}.
            {lang_instr}
            Особые пожелания: {u_wishes}.
            
            {intl_prompt}
            Тип: {'СОР/СОЧ' if opt_sor else 'Рабочий лист'}.
            {'Включить аудирование (скрипт).' if opt_audit else ''}
            
            СТРУКТУРА:
            1. Задания должны соответствовать выбранным стандартам (PISA/PIRLS если выбрано).
            2. Сумма баллов: {u_score}.
            3. БЕЗ Markdown.
            4. Таблица дескрипторов в конце.
            """
            
            with st.spinner("Применяем стандарты PISA/PIRLS..."):
                res = generate_safe(prompt)
                if res:
                    clean = clean_content(res.text)
                    # Определение типа для шапки
                    d_type = "WORK"
                    if opt_sor: d_type = "SOR"
                    elif opt_pisa: d_type = "PISA"
                    elif opt_pirls: d_type = "PIRLS"
                    
                    docx = save_to_docx(clean, u_topic, u_subj, u_grade, t_name, u_score, d_type, variant=u_variant)
                    st.download_button("💾 СКАЧАТЬ WORD", docx, file_name=f"{u_subj}_{u_topic}.docx")

# === ВКЛАДКА 2: ТЕСТЫ ===
with tab_test:
    st.subheader("Генератор тестов")
    tc1, tc2 = st.columns(2)
    with tc1:
        t_subj = st.selectbox("Предмет (Тест):", SUBJECTS_DB["Языки и Литература"] + SUBJECTS_DB["Мат / Ест / Инф"])
        t_count = st.slider("Вопросов:", 5, 30, 10)
    with tc2:
        t_grade = st.selectbox("Класс (Тест):", [str(i) for i in range(1, 12)])
        t_opts = st.selectbox("Вариантов ответа:", [3, 4, 5], index=1)

    t_topic = st.text_input("Тема теста:")
    t_wishes = st.text_area("Пожелания к тесту:", placeholder="Уровень сложности, акценты...")

    if st.button("📝 Создать ТЕСТ"):
        if t_topic:
            prompt_test = f"""
            Создай тест. Язык: {class_lang}. Предмет: {t_subj}, {t_grade} класс.
            Тема: {t_topic}. Пожелания: {t_wishes}.
            Вопросов: {t_count}. Вариантов ответа: {t_opts}.
            
            В КОНЦЕ ОБЯЗАТЕЛЬНО: Ключи к тесту.
            Формат: Чистый текст без Markdown.
            """
            with st.spinner("Генерация теста..."):
                res = generate_safe(prompt_test)
                if res:
                    clean = clean_content(res.text)
                    docx = save_to_docx(clean, f"Тест: {t_topic}", t_subj, t_grade, t_name, t_count, "TEST")
                    st.download_button("💾 СКАЧАТЬ ТЕСТ", docx, file_name=f"TEST_{t_topic}.docx")

# === ВКЛАДКА 3: РЕЗЕРВ ===
with tab_reserve:
    st.info("Адаптация для ООП")
    r_name = st.text_input("Имя ученика:")
    r_subj = st.selectbox("Предмет (Резерв):", SUBJECTS_DB["Начальная школа"] + SUBJECTS_DB["Языки и Литература"])
    r_wish = st.text_area("Диагноз/Пожелания:", placeholder="Крупный шрифт, упростить текст...")
    
    if st.button("🪄 Адаптировать"):
        if r_name:
            prompt = f"""
            Адаптируй для ООП. Язык: {class_lang}. Ученик: {r_name}.
            Предмет: {r_subj}. Пожелания: {r_wish}.
            Задания уровня 'Узнавание'. Макс упрощение.
            """
            res = generate_safe(prompt)
            if res:
                clean = clean_content(res.text)
                docx = save_to_docx(clean, f"Резерв", r_subj, "Спец", t_name, 10, "WORK", r_name)
                st.download_button("💾 СКАЧАТЬ (РЕЗЕРВ)", docx, file_name=f"Reserve_{r_name}.docx")
