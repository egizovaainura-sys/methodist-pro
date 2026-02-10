import streamlit as st
import google.generativeai as genai
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

# --- 1. КОНФИГУРАЦИЯ ---
st.set_page_config(page_title="Методист PRO", layout="wide", page_icon="🇰🇿")

# Инициализация API
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    
    # Попытка инициализации модели с отказоустойчивостью
    try:
        # Пробуем самую свежую версию Flash
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
    except:
        try:
            # Если не вышло, пробуем стандартную Flash
            model = genai.GenerativeModel('gemini-1.5-flash')
        except:
            # Крайний случай - проверенная Gemini Pro
            model = genai.GenerativeModel('gemini-pro')
else:
    st.error("Ключ API не найден в Streamlit Secrets.")
    st.stop()

# Инициализация сессии
for key in ['main_text', 'main_file', 'res_text', 'res_file']:
    if key not in st.session_state: st.session_state[key] = None

# --- 2. ЛОГИКА СОЗДАНИЯ WORD ---
def apply_font_settings(run, size=12, bold=False):
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    run.font.size = Pt(size)
    run.bold = bold

def create_docx(text, title, subj, gr, teacher, max_score, is_sor, std_name=""):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)

    doc_type = "БЖБ / СОР" if is_sor else "Рабочий лист"

    table = doc.add_table(rows=2, cols=2)
    table.columns[0].width = Inches(4.5)
    
    c0 = table.cell(0, 0).paragraphs[0]
    apply_font_settings(c0.add_run(f"Оқушы / Ученик: {std_name if std_name else '____________________'}"))
    
    c1 = table.cell(1, 0).paragraphs[0]
    apply_font_settings(c1.add_run(f"Пән / Предмет: {subj} | Сынып: {gr}"))
    
    r1 = table.cell(0, 1).paragraphs[0]
    r1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    apply_font_settings(r1.add_run("Күні: ____.____.202__"))
    
    r2 = table.cell(1, 1).paragraphs[0]
    r2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    score_label = f"Балл: ___ / {max_score}" if is_sor else "Баға: _____"
    apply_font_settings(r2.add_run(f"{doc_type}\n{score_label}"), bold=True)

    doc.add_paragraph()
    h = doc.add_heading('', 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    apply_font_settings(h.add_run(title.upper()), size=14, bold=True)

    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        
        if line.startswith('|') and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                tbl = doc.add_table(rows=1, cols=len(cells))
                tbl.style = 'Table Grid'
                for j, c_text in enumerate(cells):
                    p = tbl.cell(0, j).paragraphs[0]
                    apply_font_settings(p.add_run(c_text), size=10)
            continue

        p = doc.add_paragraph()
        clean_line = line.replace('**', '').replace('###', '').replace('##', '').replace('#', '')
        
        is_bold = any(line.startswith(k) for k in ["Задание", "Тапсырма", "Вариант", "Ключи", "Ответы", "Дескриптор"])
        apply_font_settings(p.add_run(clean_line), bold=is_bold)

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
    st_prog = st.selectbox("Предмет:", full_subjects)
    
    st.divider()
    st_type = st.radio("Тип материала:", ["Рабочий лист", "БЖБ / СОР"])
    st_variants = st.slider("Количество вариантов:", 1, 3, 1)
    st_max_score = st.number_input("Макс. балл за вариант:", 1, 100, 10)
    
    st.subheader("Настройки:")
    inc_test = st.checkbox("Тесты (A, B, C, D)", value=True)
    inc_keys = st.checkbox("🔑 Добавить ответы", value=True)

tab1, tab2 = st.tabs(["👥 ВЕСЬ КЛАСС", "🎯 РЕЗЕРВ (МОТИВАЦИЯ)"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        m_subj = st.text_input("Предмет:", value=st_prog.split(' - ')[0])
        m_grade = st.selectbox("Класс:", [str(i) for i in range(1, 12)])
    with col2:
        m_topic = st.text_input("Тема урока:", placeholder="Напр: Имя прилагательное")
    
    m_goals = st.text_area("Цели обучения (ЦО):", placeholder="Напр: 5.1.2.1...", height=100)

    if st.button("🚀 Сгенерировать полный комплект", type="primary"):
        if m_topic and m_goals:
            with st.spinner("Связываемся с ИИ..."):
                prompt = f"""
                Ты — эксперт-методист. ПРЕДМЕТ: {st_prog}. ТЕМА: {m_topic}. КЛАСС: {m_grade}.
                ЦЕЛИ: {m_goals}. Сгенерируй {st_variants} вариант(а). 
                Включи: {'тесты,' if inc_test else ''} открытые задания.
                Принцип: 1 действие = 1 балл. Сумма баллов: {st_max_score}.
                В конце создай таблицу дескрипторов и { 'секцию ОТВЕТОВ' if inc_keys else '' }.
                """
                try:
                    res = model.generate_content(prompt)
                    st.session_state.main_text = res.text
                    st.session_state.main_file = create_docx(res.text, m_topic, m_subj, m_grade, t_fio, st_max_score, "СОР" in st_type)
                except Exception as e:
                    st.error(f"Ошибка ИИ: {e}")
        else:
            st.warning("Заполните тему и цели!")

    if st.session_state.main_text:
        st.divider(); st.markdown(st.session_state.main_text)
        st.download_button("📥 СКАЧАТЬ WORD", data=st.session_state.main_file, file_name=f"{m_topic}_Class.docx")

with tab2:
    st.subheader("🎯 Резервный учащийся")
    r_name = st.text_input("ФИО Ученика:", key="rname")
    r_score = st.number_input("Балл (Резерв):", 1, 50, 5)

    if st.button("🪄 Адаптировать (Мотивация)", type="primary"):
        if m_topic and m_goals:
            with st.spinner("Добавляем мотивацию..."):
                res_prompt = f"""
                Педагог-ментор. Ученик {r_name} (резерв). Тема: {m_topic}. ЦО: {m_goals}.
                Задания должны быть интересными, с жизненными примерами.
                Баллов: {r_score}. Дескрипторы: 1 действие = 1 балл.
                """
                try:
                    res = model.generate_content(res_prompt)
                    st.session_state.res_text = res.text
                    st.session_state.res_file = create_docx(res.text, f"Резерв: {m_topic}", m_subj, m_grade, t_fio, r_score, False, r_name)
                except Exception as e: st.error(f"Ошибка: {e}")
        else: st.warning("Сначала заполните первую вкладку!")

    if st.session_state.res_text:
        st.divider(); st.markdown(st.session_state.res_text)
        st.download_button("📄 СКАЧАТЬ РЕЗЕРВ", data=st.session_state.res_file, file_name=f"Reserve_{r_name}.docx")
