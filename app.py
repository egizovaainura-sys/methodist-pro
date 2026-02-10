import streamlit as st
import google.generativeai as genai
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. НАСТРОЙКИ ---
st.set_page_config(page_title="Методист PRO", layout="wide")

MY_API_KEY = st.secrets["GOOGLE_API_KEY"]
MODEL_NAME = 'gemini-flash-latest'

def load_ai():
    try:
        genai.configure(api_key=MY_API_KEY)
        return genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        st.error(f"Ошибка подключения к ИИ: {e}")
        return None

model = load_ai()

# --- 2. ФУНКЦИИ ДЛЯ WORD ---
def create_worksheet(text, title, subj, gr, teacher, max_score, is_sor, std_name=""):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)

    # Тип документа
    doc_type = "БЖБ / СОР (Суммативное оценивание)" if is_sor else "Жұмыс парағы / Рабочий лист"

    # Шапка
    header_table = doc.add_table(rows=2, cols=2)
    header_table.columns[0].width = Inches(4.5)
    
    header_table.cell(0, 0).text = f"Оқушы / Ученик: {std_name if std_name else '____________________'}"
    header_table.cell(1, 0).text = f"Пән / Предмет: {subj} | Сынып: {gr}"
    
    r1 = header_table.cell(0, 1)
    r1.text = "Күні: ____.____.202__"
    r1.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    # Отображение балла
    score_text = f"Балл: ___ / {max_score}" if is_sor else "Баға / Оценка: _____"
    r2 = header_table.cell(1, 1)
    r2.text = f"{doc_type}\n{score_text}"
    r2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph()

    # Заголовок
    h = doc.add_heading(title.upper(), 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in h.runs: 
        run.font.name = 'Times New Roman'
        run.font.color.rgb = RGBColor(0,0,0)
        run.font.size = Pt(14)

    # Обработка текста
    lines = text.split('\n')
    for line in lines:
        row = line.strip()
        clean = row.replace('**', '').replace('###', '').replace('##', '').replace('#', '').strip()
        
        # Таблицы (Критерии)
        if row.startswith('|') and '---' not in row:
            cells = [c.strip() for c in row.split('|') if c.strip()]
            if cells:
                tbl = doc.add_table(rows=1, cols=len(cells))
                tbl.style = 'Table Grid'
                for j, c_text in enumerate(cells):
                    tbl.cell(0, j).text = c_text
                    for p in tbl.cell(0, j).paragraphs:
                        for r in p.runs: r.font.name = 'Times New Roman'; r.font.size = Pt(10)
            continue
        
        if not clean: continue
        
        # Текст
        p = doc.add_paragraph(clean)
        
        # Жирный шрифт для заданий
        if any(clean.startswith(s) for s in ["Задание", "Тапсырма", "Task", "1.", "2.", "3.", "Текст"]):
            p.bold = True
            
        # Линии для ответа
        if is_sor and any(clean.startswith(s) for s in ["1.", "2.", "3.", "Задание"]):
             if "Текст" not in clean: 
                pass 

    # Подвал
    doc.add_paragraph("\n" + "_"*45)
    footer = doc.add_paragraph()
    footer.add_run(f"Мұғалім: {teacher} ____________ (қолы)")
    
    buf = BytesIO(); doc.save(buf); buf.seek(0)
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
        m_subj = st.text_input("Предмет:", key="ms")
        m_grade = st.selectbox("Класс:", [str(i) for i in range(1, 12)], key="mg")
    with c2:
        m_sect = st.text_input("Раздел:", key="msc")
        m_topic = st.text_input("Тема (Заголовок):", key="mt")
    with c3:
        m_score = st.number_input("Макс. балл (Сумма):", 1, 80, 10, key="mscr")
    
    m_goals = st.text_area("Цели обучения (ЦО) - ОБЯЗАТЕЛЬНО:", height=100, key="mgl", placeholder="Вставьте код цели (например, 5.1.2.1) и её описание...")

    if st.button("🚀 Создать полный материал"):
        if model:
            # Сборка настроек
            active_m = []
            if m_work: active_m.append("Рабочий лист")
            if m_func: active_m.append("Функциональная грамотность (анализ ситуаций)")
            if m_pisa: active_m.append("PISA/PIRLS (международные стандарты)")
            if m_audit: active_m.append("Аудирование")

            # СОР/СОЧ
            sor_prompt = ""
            if m_sor:
                sor_prompt = f"""
                РЕЖИМ КОНТРОЛЯ (СОР/СОЧ):
                1. Общий балл должен быть РОВНО {m_score}.
                2. Задания должны СТРОГО проверять указанные Цели Обучения. Никаких заданий "не по теме".
                3. Структура: Задание -> Место для ответа.
                """
            
            lang_logic = "Я2 (второй язык): лексика адаптированная." if "Я2" in prog else "Я1 (родной): глубокий анализ."
            
            # --- ГЛАВНЫЙ ПРОМПТ С ПРИВЯЗКОЙ К ЦЕЛЯМ ---
            prompt = f"""
            Роль: Методист-эксперт. Тип: {prog}. Тема: {m_topic}. Класс: {m_grade}.
            
            ОСНОВНОЕ ТРЕБОВАНИЕ:
            Все задания должны быть разработаны СТРОГО на основе Целей Обучения: "{m_goals}".
            Если цель требует "анализа" — давай задание на анализ. Если "понимания" — тест или вопросы.
            Не добавляй задания, которые не относятся к этим целям.

            Включи элементы: {', '.join(active_m)}.
            {sor_prompt} {lang_logic}
            
            КРИТЕРИИ ОЦЕНИВАНИЯ (В КОНЦЕ ДОКУМЕНТА):
            Создай таблицу дескрипторов. Принцип: "Один шаг = Один балл".
            Распиши баллы подробно. Сумма должна быть равна {m_score}.
            | Задание | Дескриптор (Обучающийся) | Балл |
            """
            
            with st.spinner("Анализ целей обучения и генерация..."):
                try:
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
                    doc = create_worksheet(res.text, m_topic, m_subj, m_grade, t_fio, m_score, m_sor)
                    fname = f"SOR_{m_topic}.docx" if m_sor else f"Worksheet_{m_topic}.docx"
                    st.download_button(f"💾 СКАЧАТЬ WORD ({m_score} б.)", data=doc, file_name=fname)
                except Exception as e: st.error(f"Ошибка ИИ: {e}")
        else:
            st.error("Ошибка ключа.")

with tab2:
    st.subheader("Индивидуальная адаптация")
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        r_name = st.text_input("ФИО Ученика (Резерв):", key="rn")
        r_subj = st.text_input("Предмет:", value=m_subj, disabled=True)
    with rc2:
        r_topic = st.text_input("Тема:", value=m_topic, disabled=True)
        r_score = st.number_input("Балл (Резерв):", 1, 40, 5, key="rsc")
    with rc3:
        r_grade = st.text_input("Класс:", value=m_grade, disabled=True)
    
    r_goals = st.text_area("Цели (Дубликат):", value=m_goals, disabled=True, height=100)

    if st.button("🪄 Адаптировать под цели для резерва"):
        if model:
            prompt = f"""
            Коррекционный педагог. Адаптируй урок для ученика: {r_name}.
            Цели обучения те же: {r_goals}, НО уровень сложности снижен.
            Упрости формулировки, но сохрани суть цели.
            Принцип оценивания: 1 верный ответ = 1 балл.
            Макс балл: {r_score}.
            """
            with st.spinner("Адаптация по целям..."):
                try:
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
                    doc = create_worksheet(res.text, f"Reserve_{r_name}", m_subj, m_grade, t_fio, r_score, False, r_name)
                    st.download_button("📄 СКАЧАТЬ WORD (РЕЗЕРВ)", data=doc, file_name=f"Reserve_{r_name}.docx")
                except Exception as e: st.error(f"Ошибка ИИ: {e}")