import streamlit as st
import google.generativeai as genai
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

# --- 1. ИНИЦИАЛИЗАЦИЯ И НАСТРОЙКИ ---
st.set_page_config(page_title="Методист PRO v2.0", layout="wide", page_icon="🇰🇿")

# Стилизация CSS для красоты
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .stDownloadButton>button { background-color: #2e7d32; color: white; }
    </style>
    """, unsafe_allow_html=True)

# Подключение к Google Gemini
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Используем 1.5 Flash для скорости или 1.5 Pro для глубины
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("⚠️ API Ключ не найден в Streamlit Secrets!")
    st.stop()

# Инициализация хранилища сессии
if 'content' not in st.session_state:
    st.session_state.content = {"main": None, "res": None, "main_file": None, "res_file": None}

# --- 2. ПРОДВИНУТАЯ ЛОГИКА WORD ---
def apply_font_settings(run, size=12, bold=False, color=(0,0,0)):
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = RGBColor(*color)

def create_advanced_docx(content_text, title, subj, grade, teacher, max_score, is_sor, student_name=""):
    doc = Document()
    
    # Секция: Шапка
    section = doc.sections[0]
    section.top_margin = Inches(0.5)
    
    header_tbl = doc.add_table(rows=2, cols=2)
    header_tbl.width = Inches(6.5)
    
    # Левая колонка
    c00 = header_tbl.cell(0, 0).paragraphs[0]
    apply_font_settings(c00.add_run(f"Ученик: {student_name if student_name else '____________________'}"))
    c10 = header_tbl.cell(1, 0).paragraphs[0]
    apply_font_settings(c10.add_run(f"Предмет: {subj} | Класс: {grade}"))
    
    # Правая колонка
    c01 = header_tbl.cell(0, 1).paragraphs[0]
    c01.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    apply_font_settings(c01.add_run("Дата: ____.____.202__"))
    
    c11 = header_tbl.cell(1, 1).paragraphs[0]
    c11.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc_label = "БЖБ (СОР)" if is_sor else "Рабочий лист"
    score_label = f"Балл: ___ / {max_score}" if is_sor else "Оценка: _____"
    apply_font_settings(c11.add_run(f"{doc_label}\n{score_label}"), bold=True)

    doc.add_paragraph()

    # Заголовок
    heading = doc.add_heading('', 0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    apply_font_settings(heading.add_run(title.upper()), size=14, bold=True)

    # Парсинг контента
    for line in content_text.split('\n'):
        line = line.strip()
        if not line: continue

        # Работа с таблицами (Дескрипторы / Ответы)
        if line.startswith('|') and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                tbl = doc.add_table(rows=1, cols=len(cells))
                tbl.style = 'Table Grid'
                for i, cell_text in enumerate(cells):
                    p = tbl.cell(0, i).paragraphs[0]
                    apply_font_settings(p.add_run(cell_text), size=10)
            continue

        # Создание параграфа
        p = doc.add_paragraph()
        
        # Определяем стиль параграфа
        is_bold = False
        font_size = 12
        
        if line.startswith('###'): 
            line = line.replace('###', '').strip()
            is_bold = True
            font_size = 13
        elif line.startswith('Задание') or line.startswith('Тапсырма') or line.startswith('Вариант'):
            is_bold = True
        
        clean_text = line.replace('**', '').replace('##', '').replace('#', '').strip()
        apply_font_settings(p.add_run(clean_text), size=font_size, bold=is_bold)

    # Футер
    doc.add_paragraph("\n" + "_"*50)
    footer = doc.add_paragraph()
    apply_font_settings(footer.add_run(f"Учитель: {teacher} ________________ (подпись)"), size=10)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 3. ИНТЕРФЕЙС SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/kazakhstan.png", width=60)
    st.title("Методист PRO")
    
    with st.expander("👤 Личные данные", expanded=True):
        t_fio = st.text_input("ФИО Учителя:", value="Учитель")
    
    with st.expander("📚 Параметры предмета", expanded=True):
        subjects = [
            "Русский язык (Я1)", "Русский язык (Я2)", "Қазақ тілі (Т1)", "Қазақ тілі (Т2)",
            "Математика", "Алгебра", "Геометрия", "Информатика", "Физика", "Химия", "Биология",
            "История Казахстана", "Всемирная история", "География", "Естествознание"
        ]
        sel_subj = st.selectbox("Предмет:", subjects)
        sel_grade = st.select_slider("Класс:", options=[str(i) for i in range(1, 12)], value="5")
        
    with st.expander("⚙️ Настройки материала"):
        m_type = st.selectbox("Тип:", ["Рабочий лист", "СОР (Контроль)"])
        m_vars = st.number_input("Вариантов:", 1, 3, 1)
        m_score = st.number_input("Баллов на вариант:", 1, 100, 10)
        
        st.write("---")
        inc_mcq = st.checkbox("Тесты (A,B,C,D)", value=True)
        inc_func = st.checkbox("Функц. грамотность", value=False)
        inc_pisa = st.checkbox("PISA задания", value=False)
        inc_ans = st.checkbox("Ключи ответов", value=True)

# --- 4. ОСНОВНОЙ ЭКРАН ---
tab_class, tab_res = st.tabs(["👥 Весь класс", "🎯 Резерв (Мотивация)"])

with tab_class:
    col1, col2 = st.columns([1, 1])
    with col1:
        m_topic = st.text_input("Тема занятия:", placeholder="Напр: Фотосинтез и его значение")
    with col2:
        m_bloom = st.multiselect("Уровни Блума:", ["Знание", "Понимание", "Применение", "Анализ", "Синтез", "Оценка"], ["Знание", "Применение"])
    
    m_goals = st.text_area("Цели обучения (ЦО):", placeholder="Напр: 5.2.1.1 — Объяснять процесс...", height=120)

    if st.button("🚀 Сгенерировать полный комплект", type="primary"):
        if m_topic and m_goals:
            with st.spinner("🧠 ИИ анализирует цели и формирует задания по стандартам РК..."):
                
                prompt = f"""
                Ты — ведущий эксперт Национального центра тестирования Казахстана и опытный методист.
                ПРЕДМЕТ: {sel_subj}. КЛАСС: {sel_grade}. ТЕМА: {m_topic}.
                ЦЕЛИ ОБУЧЕНИЯ (ЦО): {m_goals}.
                УРОВНИ БЛУМА: {', '.join(m_bloom)}.
                
                ЗАДАНИЕ:
                1. Сгенерируй {m_vars} варианта(ов) учебного материала ({m_type}).
                2. Для каждого варианта распредели {m_score} баллов. ПРИНЦИП: 1 четкое действие = 1 балл.
                3. ВКЛЮЧИ:
                   - {'Тесты с 4 вариантами ответов' if inc_mcq else ''}
                   - {'Задания на функциональную грамотность (кейс)' if inc_func else ''}
                   - {'Критическое мышление (формат PISA)' if inc_pisa else ''}
                   - Открытые вопросы (минимум 2).
                
                ОФОРМЛЕНИЕ ДЛЯ КАЖДОГО ВАРИАНТА:
                ### Вариант №...
                Задания...
                ### Таблица дескрипторов:
                | Задание | Дескриптор (Обучающийся...) | Балл |
                
                { "В КОНЦЕ ДОКУМЕНТА: Создай раздел ### КЛЮЧИ ОТВЕТОВ для учителя." if inc_ans else "" }
                """
                
                try:
                    res = model.generate_content(prompt)
                    st.session_state.content["main"] = res.text
                    st.session_state.content["main_file"] = create_advanced_docx(
                        res.text, m_topic, sel_subj, sel_grade, t_fio, m_score, "СОР" in m_type
                    )
                except Exception as e:
                    st.error(f"Ошибка генерации: {e}")
        else:
            st.warning("⚠️ Пожалуйста, заполните тему и цели обучения!")

    if st.session_state.content["main"]:
        st.markdown("---")
        st.subheader("📝 Предпросмотр")
        st.markdown(st.session_state.content["main"])
        st.download_button(
            "📥 СКАЧАТЬ В WORD (.DOCX)", 
            data=st.session_state.content["main_file"], 
            file_name=f"{m_topic}_Class.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

# --- 5. ВКЛАДКА РЕЗЕРВА ---
with tab_res:
    st.subheader("🎯 Адаптация для резервного ученика")
    st.write("Этот инструмент перерабатывает основной контент, добавляя игровые механики, жизненные примеры и 'быстрые победы' для ученика с низкой мотивацией.")
    
    r_name = st.text_input("ФИО Резервного учащегося:", placeholder="Иван Иванов")
    r_score = st.number_input("Максимальный балл (адапт.):", 1, 50, 5)
    
    st.info(f"Синхронизация с темой: **{m_topic if m_topic else 'Не указана'}**")

    if st.button("🪄 Создать мотивирующий лист", type="primary"):
        if m_topic and m_goals:
            with st.spinner("✨ Добавляем элементы геймификации и практической значимости..."):
                res_prompt = f"""
                Роль: Педагог-психолог и Ментор. 
                Ученик: {r_name}. Уровень: Резерв (нужна мотивация).
                Тема: {m_topic}. ЦО: {m_goals}.
                
                ИНСТРУКЦИЯ:
                1. Сделай задания 'живыми'. Вместо 'Реши уравнение' используй 'Помоги герою рассчитать...'.
                2. Добавь блок '💡 А ты знал?', связывающий тему с реальностью или будущей профессией.
                3. Разбей задания на очень мелкие шаги (scaffolding).
                4. Итоговый балл: {r_score}. Принцип: 1 действие = 1 балл.
                5. Создай таблицу дескрипторов и раздел ответов.
                """
                try:
                    res = model.generate_content(res_prompt)
                    st.session_state.content["res"] = res.text
                    st.session_state.content["res_file"] = create_advanced_docx(
                        res.text, f"Твой путь к успеху: {m_topic}", sel_subj, sel_grade, t_fio, r_score, False, r_name
                    )
                except Exception as e:
                    st.error(f"Ошибка: {e}")
        else:
            st.error("⚠️ Сначала заполните данные в первой вкладке!")

    if st.session_state.content["res"]:
        st.markdown("---")
        st.markdown(st.session_state.content["res"])
        st.download_button(
            "📥 СКАЧАТЬ ЛИСТ РЕЗЕРВА", 
            data=st.session_state.content["res_file"], 
            file_name=f"Reserve_{r_name}.docx"
        )
