import streamlit as st
import google.generativeai as genai
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re

# --- 1. НАСТРОЙКИ ---
st.set_page_config(page_title="Методист PRO", layout="wide")

# Получение API ключа (в среде Streamlit Cloud используется st.secrets)
MY_API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
MODEL_NAME = 'gemini-2.5-flash-preview-09-2025'

def load_ai():
    if not MY_API_KEY:
        st.error("API ключ не найден в secrets!")
        return None
    try:
        genai.configure(api_key=MY_API_KEY)
        return genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        st.error(f"Ошибка подключения к ИИ: {e}")
        return None

model = load_ai()

# --- 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def clean_markdown(text):
    """Удаляет лишние символы форматирования Markdown для чистого вывода в Word."""
    # Удаляем жирный шрифт, курсив, подчеркивание
    text = re.sub(r'[*_]{1,3}', '', text)
    # Удаляем символы заголовков в начале строки
    text = re.sub(r'^#+\s*', '', text)
    return text.strip()

def create_worksheet(ai_text, title, subj, gr, teacher, max_score, is_sor, std_name=""):
    doc = Document()
    
    # Глобальные настройки шрифта
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)

    # Тип документа
    doc_type = "БЖБ / СОР (Суммативное оценивание)" if is_sor else "Жұмыс парағы / Рабочий лист"

    # Шапка (Таблица без границ для выравнивания)
    header_table = doc.add_table(rows=2, cols=2)
    header_table.columns[0].width = Inches(4.0)
    header_table.columns[1].width = Inches(2.5)
    
    header_table.cell(0, 0).text = f"Оқушы / Ученик: {std_name if std_name else '____________________'}"
    header_table.cell(1, 0).text = f"Пән / Предмет: {subj} | Сынып: {gr}"
    
    date_cell = header_table.cell(0, 1)
    date_cell.text = "Күні: ____.____.202__"
    date_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    score_text = f"Балл: ___ / {max_score}" if is_sor else "Баға / Оценка: _____"
    type_cell = header_table.cell(1, 1)
    type_cell.text = f"{doc_type}\n{score_text}"
    type_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph()

    # Заголовок документа
    h = doc.add_heading(title.upper(), 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in h.runs: 
        run.font.name = 'Times New Roman'
        run.font.color.rgb = RGBColor(0,0,0)
        run.font.size = Pt(14)
        run.bold = True

    # Обработка контента (Текст + Таблицы)
    lines = ai_text.split('\n')
    table_data = []
    
    for line in lines:
        stripped_line = line.strip()
        
        # Логика распознавания таблицы (Markdown)
        if stripped_line.startswith('|'):
            # Пропускаем разделительные линии типа |---|---|
            if '---' in stripped_line:
                continue
            cells = [c.strip() for c in stripped_line.split('|') if c.strip()]
            if cells:
                table_data.append(cells)
            continue
        else:
            # Если до этого собирали таблицу, записываем её в Word
            if table_data:
                tbl = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
                tbl.style = 'Table Grid'
                for i, row_cells in enumerate(table_data):
                    for j, cell_text in enumerate(row_cells):
                        cell = tbl.cell(i, j)
                        cell.text = clean_markdown(cell_text)
                        # Настройка шрифта внутри таблицы
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                run.font.name = 'Times New Roman'
                                run.font.size = Pt(10)
                table_data = []
                doc.add_paragraph() # Отступ после таблицы

            # Обычный текст
            clean_line = clean_markdown(stripped_line)
            if not clean_line:
                continue
                
            p = doc.add_paragraph(clean_line)
            
            # Специфическое форматирование для разделов
            if any(clean_line.lower().startswith(s) for s in ["задание", "тапсырма", "task", "критерии", "дескриптор"]):
                p.bold = True
                p.paragraph_format.space_before = Pt(12)

    # Подвал
    doc.add_paragraph("\n" + "_"*45)
    footer = doc.add_paragraph()
    footer.add_run(f"Мұғалім: {teacher} ____________ (қолы)")
    
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 3. ИНТЕРФЕЙС ---
with st.sidebar:
    st.title("🇰🇿 Методист PRO")
    t_fio = st.text_input("ФИО Учителя:", value="Учитель")
    
    st.subheader("Языковая программа:")
    prog = st.selectbox("Выберите тип:", [
        "Русский язык (Я1) - Родной", 
        "Русский язык (Я2) - Второй", 
        "Қазақ тілі (Т1)", "Қазақ тілі (Т2)",
        "Математика", "Алгебра", "Геометрия", "Естествознание", "Биология", "История"
    ])
    
    st.divider()
    st.subheader("1. Тип материала:")
    m_work = st.checkbox("Рабочий лист (Практика)", value=True)
    m_sor = st.checkbox("БЖБ (СОР) / ТЖБ (СОЧ) - Контроль")
    
    st.subheader("2. Компетенции:")
    m_func = st.checkbox("🧠 Функциональная грамотность (МОДО)", value=True)
    m_pisa = st.checkbox("🌍 PISA / PIRLS (Критическое мышление)")
    m_audit = st.checkbox("🎧 Аудирование (Работа с текстом)")

# Вкладки
tab1, tab2 = st.tabs(["👥 ВЕСЬ КЛАСС", "👤 РЕЗЕРВ (ИНКЛЮЗИЯ)"])

with tab1:
    c1, c2, c3 = st.columns(3)
    with c1:
        m_subj = st.text_input("Предмет:", key="ms", value="Русский язык")
        m_grade = st.selectbox("Класс:", [str(i) for i in range(1, 12)], index=4, key="mg")
    with c2:
        m_sect = st.text_input("Раздел:", key="msc", placeholder="Напр: Культура")
        m_topic = st.text_input("Тема (Заголовок):", key="mt", placeholder="Напр: Искусство слова")
    with c3:
        m_score = st.number_input("Макс. балл (Сумма):", 1, 80, 10, key="mscr")
    
    m_goals = st.text_area("Цели обучения (ЦО) - ОБЯЗАТЕЛЬНО:", height=100, key="mgl", 
                          placeholder="Вставьте код цели (например, 5.1.2.1) и её описание...")

    if st.button("🚀 Создать полный материал", type="primary"):
        if not m_goals.strip():
            st.warning("Пожалуйста, введите цели обучения.")
        elif model:
            active_m = []
            if m_work: active_m.append("Рабочий лист")
            if m_func: active_m.append("Функциональная грамотность")
            if m_pisa: active_m.append("PISA/PIRLS задания")
            if m_audit: active_m.append("Аудирование")

            sor_logic = ""
            if m_sor:
                sor_logic = f"""
                РЕЖИМ КОНТРОЛЯ (СОР/СОЧ):
                - Итоговая сумма баллов должна быть ровно {m_score}.
                - Для каждого задания укажи балл.
                - В конце обязательно создай таблицу критериев и дескрипторов.
                """
            
            lang_logic = "Адаптируй сложность для Я2 (второй язык)." if "Я2" in prog else "Используй академический уровень Я1."

            prompt = f"""
            Ты - ведущий методист образования Казахстана. Твоя задача: создать учебный материал.
            Предмет: {m_subj}, Класс: {m_grade}. Тема: {m_topic}.
            
            ЦЕЛИ ОБУЧЕНИЯ: {m_goals}
            
            ТРЕБОВАНИЯ:
            1. Создай интересные задания (минимум 3-4 задания).
            2. Обязательно включи: {', '.join(active_m)}.
            3. {sor_logic}
            4. {lang_logic}
            
            ФОРМАТ ТАБЛИЦЫ КРИТЕРИЕВ (В КОНЦЕ):
            Применяй принцип: "1 верное действие = 1 балл".
            Используй только стандартную Markdown таблицу:
            | № Задания | Дескриптор: Обучающийся... | Балл |
            | :--- | :--- | :--- |
            """
            
            with st.spinner("ИИ анализирует цели и проектирует задания..."):
                try:
                    res = model.generate_content(prompt)
                    st.markdown("### Предпросмотр контента:")
                    st.markdown(res.text)
                    
                    doc_file = create_worksheet(res.text, m_topic, m_subj, m_grade, t_fio, m_score, m_sor)
                    
                    st.download_button(
                        label=f"💾 СКАЧАТЬ WORD ({m_score} б.)",
                        data=doc_file,
                        file_name=f"{'SOR' if m_sor else 'Worksheet'}_{m_topic}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.error(f"Ошибка при генерации: {e}")

with tab2:
    st.subheader("Индивидуальная адаптация (Инклюзия)")
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        r_name = st.text_input("ФИО Ученика:", key="rn")
        r_subj = st.text_input("Предмет:", value=m_subj, disabled=True)
    with rc2:
        r_topic = st.text_input("Тема:", value=m_topic, disabled=True)
        r_score = st.number_input("Балл (Резерв):", 1, 40, 5, key="rsc")
    with rc3:
        r_grade = st.text_input("Класс:", value=m_grade, disabled=True)
    
    r_goals = st.text_area("Цели (Дубликат):", value=m_goals, disabled=True, height=100)

    if st.button("🪄 Адаптировать для ученика"):
        if model:
            prompt = f"""
            Ты коррекционный педагог. Адаптируй материал по теме '{r_topic}' для ученика {r_name}.
            Цели те же: {r_goals}.
            УПРОСТИ: сократи тексты, добавь подсказки, используй закрытые тесты или задания 'соедини стрелками'.
            Максимальный балл: {r_score}.
            В конце создай таблицу критериев (1 действие = 1 балл).
            """
            with st.spinner("Адаптация материала..."):
                try:
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
                    doc_res = create_worksheet(res.text, f"Адаптация_{r_name}", m_subj, m_grade, t_fio, r_score, False, r_name)
                    st.download_button("📄 СКАЧАТЬ АДАПТИРОВАННЫЙ WORD", data=doc_res, file_name=f"Inclusion_{r_name}.docx")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
