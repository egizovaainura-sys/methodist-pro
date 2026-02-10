import streamlit as st
import google.generativeai as genai
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import time

# --- 1. НАСТРОЙКИ ---
st.set_page_config(page_title="Методист PRO", layout="wide", page_icon="🇰🇿")

# Инициализация API
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Ключ API не найден в secrets!")
    model = None

# Инициализация хранилища для ОБЕИХ вкладок
states = ['main_res', 'main_file', 'res_res', 'res_file']
for state in states:
    if state not in st.session_state:
        st.session_state[state] = None

# --- 2. ФУНКЦИЯ WORD ---

def create_worksheet(text, title, subj, gr, teacher, max_score, is_sor, std_name=""):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)

    doc_type = "СОР / СОЧ (Суммативное оценивание)" if is_sor else "Рабочий лист / Жұмыс парағы"

    table = doc.add_table(rows=2, cols=2)
    table.columns[0].width = Inches(4.0)
    
    table.cell(0, 0).text = f"Оқушы / Ученик: {std_name if std_name else '____________________'}"
    table.cell(1, 0).text = f"Пән / Предмет: {subj} | Класс: {gr}"
    
    r1 = table.cell(0, 1)
    r1.text = "Күні / Дата: ____.____.202__"
    r1.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    r2 = table.cell(1, 1)
    score_val = f"Балл: ___ / {max_score}" if is_sor else "Баға / Оценка: _____"
    r2.text = f"{doc_type}\n{score_val}"
    r2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph()

    h = doc.add_heading(title.upper(), 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in h.runs:
        run.font.name = 'Times New Roman'
        run.font.color.rgb = RGBColor(0,0,0)
        run.font.size = Pt(14)

    for line in text.split('\n'):
        clean = line.replace('**', '').replace('###', '').replace('##', '').strip()
        if not clean: continue
        
        if '|' in clean and '---' not in clean:
            cells = [c.strip() for c in clean.split('|') if c.strip()]
            if cells:
                tbl = doc.add_table(rows=1, cols=len(cells))
                tbl.style = 'Table Grid'
                for j, c_text in enumerate(cells):
                    tbl.cell(0, j).text = c_text
            continue

        p = doc.add_paragraph(clean)
        if any(clean.startswith(s) for s in ["Задание", "Тапсырма", "1.", "2.", "3."]):
            p.bold = True

    doc.add_paragraph("\n" + "_"*45)
    doc.add_paragraph(f"Мұғалім / Учитель: {teacher} ____________ (қолы)")
    
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 3. ИНТЕРФЕЙС ---
with st.sidebar:
    st.title("🇰🇿 Методист PRO")
    t_fio = st.text_input("ФИО Учителя:", value="Учитель")
    prog = st.selectbox("Программа:", ["Русский язык (Я1)", "Русский язык (Я2)", "Математика", "История"])
    st.divider()
    m_work = st.checkbox("Рабочий лист", value=True)
    m_sor = st.checkbox("СОР / СОЧ")
    m_score = st.number_input("Максимальный балл:", 1, 100, 10)

tab1, tab2 = st.tabs(["👥 ВЕСЬ КЛАСС", "👤 РЕЗЕРВ (ИНКЛЮЗИЯ)"])

# --- ВКЛАДКА 1: ВЕСЬ КЛАСС ---
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        m_subj = st.text_input("Предмет:", placeholder="Например: Алгебра", key="m_s")
        m_grade = st.selectbox("Класс:", [str(i) for i in range(1, 12)], key="m_g")
    with col2:
        m_topic = st.text_input("Тема (Заголовок):", key="m_t")
    
    m_goals = st.text_area("Цели обучения (ЦО):", placeholder="Вставьте код и описание цели...", height=100)

    if st.button("🚀 Сгенерировать материал", type="primary", key="btn_main"):
        if model and m_topic and m_goals:
            with st.spinner("ИИ формирует задания..."):
                try:
                    prompt = f"Ты методист. Создай учебный материал. Тема: {m_topic}. Цели: {m_goals}. Баллы: {m_score}. Тип: {'СОР' if m_sor else 'Практика'}."
                    response = model.generate_content(prompt)
                    st.session_state.main_res = response.text
                    st.session_state.main_file = create_worksheet(response.text, m_topic, m_subj, m_grade, t_fio, m_score, m_sor)
                except Exception as e:
                    st.error(f"Ошибка: {e}")

    if st.session_state.main_res:
        st.divider()
        st.markdown(st.session_state.main_res)
        st.download_button("💾 СКАЧАТЬ WORD (ВЕСЬ КЛАСС)", data=st.session_state.main_file, file_name=f"{m_topic}_Class.docx", key="dl_main")

# --- ВКЛАДКА 2: РЕЗЕРВ (ИНКЛЮЗИЯ) ---
with tab2:
    st.subheader("🪄 Адаптация для ООП")
    r_name = st.text_input("ФИО Ученика (Резерв):", placeholder="Иван Иванов", key="r_n")
    
    # Авто-подтягивание данных из первой вкладки для удобства
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        r_score = st.number_input("Макс. балл (Упрощенный):", 1, 50, 5, key="r_sc")
    with col_r2:
        st.info(f"Предмет: {m_subj if m_subj else 'Не указан'}")
        st.info(f"Тема: {m_topic if m_topic else 'Не указана'}")

    if st.button("🪄 Адаптировать материал", type="primary", key="btn_res"):
        if model and m_topic and m_goals:
            with st.spinner("Адаптация контента под особые потребности..."):
                try:
                    # Промпт для инклюзии
                    res_prompt = f"""
                    Ты коррекционный педагог. Адаптируй материал для ученика {r_name}.
                    Тема: {m_topic}. Цели обучения: {m_goals}.
                    ТРЕБОВАНИЯ:
                    1. Упрости язык (короткие предложения).
                    2. Снизь уровень сложности, но сохрани суть целей.
                    3. Максимальный балл за работу: {r_score}.
                    4. Добавь визуальные подсказки текстом (например: "Вспомни...", "Посмотри на...").
                    5. Создай задания и таблицу дескрипторов.
                    """
                    response = model.generate_content(res_prompt)
                    st.session_state.res_res = response.text
                    st.session_state.res_file = create_worksheet(
                        response.text, f"Адаптированный: {m_topic}", m_subj, m_grade, t_fio, r_score, False, r_name
                    )
                except Exception as e:
                    st.error(f"Ошибка адаптации: {e}")
        else:
            st.warning("Сначала заполните данные во вкладке 'ВЕСЬ КЛАСС' (Предмет, Тема, Цели).")

    if st.session_state.res_res:
        st.divider()
        st.subheader(f"Предпросмотр для: {r_name}")
        st.markdown(st.session_state.res_res)
        st.download_button(
            label="📄 СКАЧАТЬ WORD (РЕЗЕРВ)", 
            data=st.session_state.res_file, 
            file_name=f"Reserve_{r_name}.docx", 
            key="dl_res"
        )
