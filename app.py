import streamlit as st
import google.generativeai as genai
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. КОНФИГУРАЦИЯ ---
st.set_page_config(page_title="Методист PRO", layout="wide", page_icon="🇰🇿")

# Инициализация API Gemini
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Ключ API не найден. Добавьте его в Streamlit Secrets.")
    st.stop()

# Инициализация сессии
if 'main_text' not in st.session_state: st.session_state.main_text = None
if 'main_file' not in st.session_state: st.session_state.main_file = None
if 'res_text' not in st.session_state: st.session_state.res_text = None
if 'res_file' not in st.session_state: st.session_state.res_file = None

# --- 2. ЛОГИКА СОЗДАНИЯ WORD ---
def create_docx(text, title, subj, gr, teacher, max_score, is_sor, std_name=""):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)

    doc_type = "БЖБ / СОР" if is_sor else "Жұмыс парағы / Рабочий лист"

    # Шапка
    table = doc.add_table(rows=2, cols=2)
    table.columns[0].width = Inches(4.5)
    table.cell(0, 0).text = f"Оқушы / Ученик: {std_name if std_name else '____________________'}"
    table.cell(1, 0).text = f"Пән / Предмет: {subj} | Сынып: {gr}"
    
    r1 = table.cell(0, 1)
    r1.text = "Күні: ____.____.202__"
    r1.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    r2 = table.cell(1, 1)
    score_display = f"Балл: ___ / {max_score}" if is_sor else "Баға: _____"
    r2.text = f"{doc_type}\n{score_display}"
    r2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph()

    # Заголовок
    h = doc.add_heading(title.upper(), 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in h.runs:
        run.font.name = 'Times New Roman'
        run.font.color.rgb = RGBColor(0,0,0)
        run.font.size = Pt(14)

    # Контент
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        
        if line.startswith('|') and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                tbl = doc.add_table(rows=1, cols=len(cells))
                tbl.style = 'Table Grid'
                for j, c_text in enumerate(cells):
                    tbl.cell(0, j).text = c_text
                    for p in tbl.cell(0, j).paragraphs:
                        for r in p.runs: 
                            r.font.name = 'Times New Roman'
                            r.font.size = Pt(10)
            continue

        clean_line = line.replace('**', '').replace('###', '').replace('##', '').replace('#', '')
        p = doc.add_paragraph(clean_line)
        if any(line.startswith(s) for s in ["Задание", "Тапсырма", "1.", "2.", "Дескриптор", "Интересный факт"]):
            p.bold = True

    doc.add_paragraph("\n" + "_"*45)
    doc.add_paragraph(f"Мұғалім: {teacher} ____________ (қолы)")
    
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 3. ИНТЕРФЕЙС ---
with st.sidebar:
    st.title("🇰🇿 Методист PRO")
    t_fio = st.text_input("ФИО Учителя:", value="Учитель")
    
    full_subjects = [
        "Русский язык (Я1) - русские классы", "Русский язык (Я2) - казахские классы",
        "Қазақ тілі (Т1)", "Қазақ тілі (Т2)", "Математика", "Алгебра", "Геометрия", "Информатика",
        "Естествознание", "Биология", "Химия", "Физика", "История Казахстана", "Всемирная история"
    ]
    st_prog = st.selectbox("Предмет программы РК:", full_subjects)
    
    st.divider()
    st_is_sor = st.checkbox("БЖБ / СОР (Контроль)")
    st_max_score = st.number_input("Максимальный балл:", 1, 100, 10)

tab1, tab2 = st.tabs(["👥 ВЕСЬ КЛАСС", "👤 РЕЗЕРВ (МОТИВАЦИЯ)"])

# --- ВКЛАДКА 1: ОСНОВНОЙ МАТЕРИАЛ ---
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        m_subj = st.text_input("Предмет:", value=st_prog.split(' - ')[0])
        m_grade = st.selectbox("Класс:", [str(i) for i in range(1, 12)])
    with c2:
        m_topic = st.text_input("Тема урока:", placeholder="Введите тему")
    
    m_goals = st.text_area("Цели обучения (ЦО):", placeholder="Напр: 7.1.2.1...", height=100)

    if st.button("🚀 Сгенерировать материал", type="primary"):
        if m_topic and m_goals:
            with st.spinner("Создание заданий..."):
                prompt = f"""
                Роль: Методист РК. Предмет: {st_prog}. Тема: {m_topic}. Класс: {m_grade}.
                Цели обучения: {m_goals}.
                1. Создай задания. 
                2. Принцип: 1 действие = 1 балл.
                3. Таблица дескрипторов на {st_max_score} баллов.
                | Задание | Дескриптор | Балл |
                """
                try:
                    res = model.generate_content(prompt)
                    st.session_state.main_text = res.text
                    st.session_state.main_file = create_docx(res.text, m_topic, m_subj, m_grade, t_fio, st_max_score, st_is_sor)
                except Exception as e: st.error(f"Ошибка: {e}")
        else: st.warning("Заполните тему и цели!")

    if st.session_state.main_text:
        st.divider()
        st.markdown(st.session_state.main_text)
        st.download_button("💾 СКАЧАТЬ WORD (КЛАСС)", data=st.session_state.main_file, file_name=f"{m_topic}_Class.docx", key="dl_main")

# --- ВКЛАДКА 2: РЕЗЕРВНЫЙ УЧАЩИЙСЯ ---
with tab2:
    st.subheader("🎯 Работа с резервным учащимся")
    st.info("Это ученик, который обладает способностями, но нуждается в дополнительной мотивации и вовлечении.")
    
    r_name = st.text_input("ФИО Резервного учащегося:", key="rname")
    r_score = st.number_input("Балл для резерва:", 1, 50, 5)
    
    st.caption(f"Синхронизировано: {m_subj} | Тема: {m_topic}")

    if st.button("🪄 Адаптировать для резерва", type="primary"):
        if m_topic and m_goals:
            with st.spinner("Создание мотивирующих заданий..."):
                res_prompt = f"""
                Роль: Педагог-наставник / Мотиватор. 
                Целевая аудитория: Резервный учащийся {r_name} (может учиться, но низкая мотивация).
                Тема: {m_topic}. Цели обучения (ЦО): {m_goals}.
                
                ЗАДАЧА:
                1. Оставь ЦО без изменений (уровень сложности соответствует классу).
                2. Добавь в начало задания "Интересный факт" или "Проблемный вопрос", который зацепит внимание.
                3. Сделай инструкции более четкими и динамичными.
                4. Используй практические примеры из жизни (зачем это нужно?).
                5. Принцип: 1 действие = 1 балл. Итоговая сумма баллов: {r_score}.
                
                Выдай текст заданий и таблицу дескрипторов.
                """
                try:
                    res = model.generate_content(res_prompt)
                    st.session_state.res_text = res.text
                    st.session_state.res_file = create_docx(res.text, f"Резерв: {m_topic}", m_subj, m_grade, t_fio, r_score, False, r_name)
                except Exception as e: st.error(f"Ошибка: {e}")
        else: st.warning("Заполните данные во вкладке 'ВЕСЬ КЛАСС'!")

    if st.session_state.res_text:
        st.divider()
        st.markdown(st.session_state.res_text)
        st.download_button("📄 СКАЧАТЬ WORD (РЕЗЕРВ)", data=st.session_state.res_file, file_name=f"Reserve_{r_name}.docx", key="dl_res")
