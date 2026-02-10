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
st.set_page_config(page_title="Методист PRO", layout="wide")

# Ключ берется из Secrets Streamlit Cloud
if "GOOGLE_API_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    MY_API_KEY = "AIzaSy..." # Для локального тестирования

def load_ai():
    try:
        genai.configure(api_key=MY_API_KEY)
        # Пробуем разные версии модели для стабильности
        for m_name in ['gemini-1.5-flash-001', 'gemini-1.5-flash', 'gemini-pro']:
            try:
                return genai.GenerativeModel(m_name)
            except:
                continue
    except Exception as e:
        st.error(f"Ошибка инициализации ИИ: {e}")
    return None

model = load_ai()

# --- 2. УМНАЯ ОЧИСТКА ОТ МУСОРА ИИ ---
def clean_content(text):
    """
    Удаляет Markdown (**), технические фразы ИИ и лишние пробелы.
    """
    # 1. Удаляем жирный шрифт и заголовки Markdown
    text = text.replace('**', '').replace('###', '').replace('##', '').replace('#', '').replace('*', '')
    
    # 2. Список фраз, которые ИИ любит писать, но нам они в Word не нужны
    stop_phrases = [
        "роль:", "задача:", "конечно", "вот ваш", "вот готовый", 
        "согласно целям", "тип материала:", "методист:", "инструкция:"
    ]
    
    lines = text.split('\n')
    final_lines = []
    
    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue
        # Пропускаем строку, если она содержит "паразитную" фразу и она короткая
        if any(phrase in clean_line.lower() for phrase in stop_phrases) and len(clean_line) < 100:
            continue
        final_lines.append(clean_line)
    
    return final_lines

# --- 3. БЕЗОПАСНАЯ ГЕНЕРАЦИЯ (Retry Logic) ---
def generate_with_retry(prompt):
    max_retries = 3
    for i in range(max_retries):
        try:
            return model.generate_content(prompt)
        except exceptions.ResourceExhausted:
            st.warning("⏳ Лимит запросов. Ждем 10 сек...")
            time.sleep(10)
        except Exception as e:
            if i == max_retries - 1:
                st.error(f"Ошибка ИИ: {e}")
            time.sleep(2)
    return None

# --- 4. ПРОФЕССИОНАЛЬНЫЙ ЭКСПОРТ В WORD ---
def save_to_docx(lines, title, subj, grade, teacher, max_score, is_sor, student_name=""):
    doc = Document()
    
    # Настройка шрифта по умолчанию
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)

    # 1. ШАПКА ДОКУМЕНТА
    header_type = "БЖБ (СОР) / ТЖБ (СОЧ)" if is_sor else "ЖҰМЫС ПАРАҒЫ / РАБОЧИЙ ЛИСТ"
    table = doc.add_table(rows=2, cols=2)
    table.columns[0].width = Inches(4.5)
    
    # Левая ячейка
    c00 = table.cell(0, 0)
    c00.text = f"Оқушы / Ученик: {student_name if student_name else '____________________'}"
    c10 = table.cell(1, 0)
    c10.text = f"Пән / Предмет: {subj} | Сынып / Класс: {grade}"
    
    # Правая ячейка
    c01 = table.cell(0, 1)
    c01.text = "Күні / Дата: «___» ________ 202_ г."
    c01.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    c11 = table.cell(1, 1)
    c11.text = f"{header_type}\nБалл: ___ / {max_score}"
    c11.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph()

    # 2. ЗАГОЛОВОК ТЕМЫ
    h = doc.add_heading(title.upper(), 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in h.runs:
        run.font.name = 'Times New Roman'
        run.font.color.rgb = RGBColor(0,0,0)
        run.font.size = Pt(14)
        run.bold = True

    # 3. ОСНОВНОЙ КОНТЕНТ
    for line in lines:
        # Проверка на таблицу (Дескрипторы)
        if line.startswith('|'):
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells and "---" not in line:
                tbl = doc.add_table(rows=1, cols=len(cells))
                tbl.style = 'Table Grid'
                for j, val in enumerate(cells):
                    tbl.cell(0, j).text = val
            continue
            
        # Обычные параграфы
        p = doc.add_paragraph(line)
        # Если это задание - делаем жирным
        if any(line.lower().startswith(s) for s in ["задание", "тапсырма", "1.", "2.", "3.", "текст"]):
            p.bold = True
            # Добавляем пустые линии для ответа, если это не текст
            if "текст" not in line.lower() and "скрипт" not in line.lower():
                doc.add_paragraph("Жауабы / Ответ: ___________________________________________________________")

    # 4. ПОДПИСЬ
    doc.add_paragraph("\n" + "_"*50)
    footer = doc.add_paragraph(f"Мұғалім / Учитель: {teacher} ____________ (қолы)")
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 5. ГЛАВНЫЙ ИНТЕРФЕЙС ---
with st.sidebar:
    st.title("🇰🇿 Методист PRO")
    t_name = st.text_input("👤 ФИО Учителя:", value="Учитель")
    
    st.divider()
    st.subheader("⚙️ Тип материала:")
    opt_work = st.checkbox("Рабочий лист (Практика)", value=True)
    opt_sor = st.checkbox("БЖБ (СОР) / ТЖБ (СОЧ)")
    
    st.subheader("📚 Дополнительно:")
    opt_func = st.checkbox("Функциональная грамотность (МОДО)", value=True)
    opt_pisa = st.checkbox("PISA / PIRLS / TIMSS")
    opt_audit = st.checkbox("Аудирование (Текст + задания)")
    
    st.info("Приложение автоматически очищает Word от лишних знаков и инструкций ИИ.")

# ВКЛАДКИ
tab_main, tab_reserve = st.tabs(["👥 ВЕСЬ КЛАСС", "👤 РЕЗЕРВ (Инклюзия)"])

# --- ВКЛАДКА 1: ОБЩАЯ ГЕНЕРАЦИЯ ---
with tab_main:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        u_subj = st.text_input("Предмет:", value="Русский язык", key="main_subj")
        u_grade = st.selectbox("Класс:", [str(i) for i in range(1, 12)], key="main_grade")
    with col2:
        u_topic = st.text_input("Тема (Заголовок документа):", key="main_topic")
        u_score = st.number_input("Максимальный балл:", 1, 100, 10, key="main_score")
    with col3:
        u_lang = st.radio("Язык заданий:", ["Русский", "Казахский"])

    u_goals = st.text_area("🎯 Цели обучения (ЦО) из КТП:", 
                          placeholder="Например: 5.1.2.1 Понимать основную мысль текста...", height=100)

    if st.button("🚀 СГЕНЕРИРОВАТЬ МАТЕРИАЛ", use_container_width=True):
        if not model:
            st.error("ИИ не подключен. Проверьте API ключ.")
        elif not u_topic or not u_goals:
            st.warning("Пожалуйста, заполните Тему и Цели обучения.")
        else:
            # Сборка требований
            reqs = []
            if opt_work: reqs.append("практические упражнения")
            if opt_sor: reqs.append("формат суммативного оценивания (СОР)")
            if opt_func: reqs.append("задания на функциональную грамотность (МОДО)")
            if opt_pisa: reqs.append("контекстные задачи мирового стандарта PISA")
            if opt_audit: reqs.append("текст для прослушивания (скрипт) и проверочные вопросы")

            prompt = f"""
            Ты - элитный методист НИШ. Создай учебный материал на языке: {u_lang}.
            Предмет: {u_subj}. Класс: {u_grade}. Тема: {u_topic}.
            ЦЕЛИ ОБУЧЕНИЯ (ЦО): {u_goals}.
            
            ВКЛЮЧИТЬ В РАБОТУ: {', '.join(reqs)}.
            
            СТРОГИЕ ТРЕБОВАНИЯ:
            1. НИКАКОЙ теории, только практика.
            2. НИКАКИХ вводных фраз ("Конечно", "Вот работа", "Я методист"). Начни сразу с "Задание 1".
            3. ЗАПРЕЩЕНО использовать разметку Markdown (звездочки, решетки).
            4. Общий балл за все задания должен быть ровно {u_score}.
            5. В конце добавь таблицу критериев: | Задание | Дескриптор | Балл |
            6. Дескрипторы должны быть пошаговыми: 1 действие = 1 балл.
            """
            
            with st.spinner("ИИ анализирует цели обучения и создает задания..."):
                response = generate_with_retry(prompt)
                if response:
                    clean_text_lines = clean_content(response.text)
                    st.success("Материал готов!")
                    with st.expander("👀 Предварительный просмотр"):
                        for line in clean_text_lines:
                            st.write(line)
                    
                    docx_file = save_to_docx(clean_text_lines, u_topic, u_subj, u_grade, t_name, u_score, opt_sor)
                    st.download_button("💾 СКАЧАТЬ В WORD", data=docx_file, 
                                     file_name=f"{u_topic}_{u_grade}class.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# --- ВКЛАДКА 2: РЕЗЕРВНЫЙ УЧЕНИК ---
with tab_reserve:
    st.subheader("💡 Адаптация материала для учеников с особыми потребностями")
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        r_name = st.text_input("Имя ученика:", placeholder="Иван Иванов")
        r_level = st.select_slider("Уровень упрощения:", options=["Легкий", "Средний", "Максимальный"])
    with r_col2:
        r_score = st.number_input("Балл для резерва:", 1, 50, 5)
    
    if st.button("🪄 АДАПТИРОВАТЬ ДЛЯ УЧЕНИКА", use_container_width=True):
        if not u_goals or not u_topic:
            st.error("Сначала заполните Тему и Цели во вкладке 'Весь класс'!")
        else:
            r_prompt = f"""
            Ты - коррекционный педагог. Адаптируй задания по теме '{u_topic}' для ученика {r_name}.
            Цели обучения: {u_goals}.
            Сложность: {r_level}. Сделай задания более доступными, используй тесты, соединение линиями, выбор ответа.
            Общий балл: {r_score}.
            Никаких звезд и приветствий. Только задания.
            """
            with st.spinner("Адаптация контента..."):
                r_response = generate_with_retry(r_prompt)
                if r_response:
                    r_clean = clean_content(r_response.text)
                    st.info(f"Материал для {r_name} сформирован.")
                    r_docx = save_to_docx(r_clean, f"Резерв: {u_topic}", u_subj, u_grade, t_name, r_score, False, r_name)
                    st.download_button("💾 СКАЧАТЬ WORD (РЕЗЕРВ)", data=r_docx, 
                                     file_name=f"Reserve_{r_name}.docx")
