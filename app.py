import streamlit as st
import google.generativeai as genai
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
from streamlit_gsheets import GSheetsConnection

# --- 1. ДАННЫЕ АВТОРА И НАСТРОЙКИ ---
st.set_page_config(page_title="Методист PRO", layout="wide", page_icon="📚")

AUTHOR_NAME = "Адильбаева Айнура Дуйшембековна"
INSTAGRAM_HANDLE = "uchitel_tdk"
INSTAGRAM_URL = f"https://instagram.com/{INSTAGRAM_HANDLE}"
WHATSAPP_URL = "https://wa.me/77776513022"
PHONE_NUMBER = "+7 (777) 651-30-22"

# --- 2. ФУНКЦИИ АВТОРИЗАЦИИ ---
def check_access(user_phone):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Читаем таблицу (ссылка должна быть в secrets.toml)
        df = conn.read(spreadsheet=st.secrets["gsheet_url"], ttl=0)
        
        # Очищаем ввод и проверяем ВТОРОЙ столбец (индекс 1)
        user_phone_clean = ''.join(filter(str.isdigit, str(user_phone)))
        allowed_phones = df.iloc[:, 1].astype(str).str.replace(r'\D', '', regex=True).tolist()
        
        return user_phone_clean in allowed_phones
    except Exception as e:
        st.error(f"Ошибка проверки базы данных: {e}")
        return False

# Инициализация сессии
if 'auth' not in st.session_state:
    st.session_state['auth'] = False

# --- 3. ОКНО ВХОДА (LOGIN) ---
if not st.session_state['auth']:
    st.title("🇰🇿 Вход в систему Методист PRO")
    st.markdown("Пожалуйста, введите ваш номер телефона для доступа к системе.")
    
    phone = st.text_input("Номер телефона (например, 77071234567):")
    
    if st.button("Войти"):
        with st.spinner("Проверка доступа..."):
            if check_access(phone):
                st.session_state['auth'] = True
                st.success("Доступ разрешен!")
                st.rerun()
            else:
                st.error("Доступ запрещен. Ваш номер не найден в базе активных подписок.")
                st.info(f"Для покупки доступа напишите автору: {AUTHOR_NAME}")
                st.markdown(f"[Написать в WhatsApp]({WHATSAPP_URL})")
    
    # Авторство на экране входа
    st.markdown("---")
    st.caption(f"Разработчик: {AUTHOR_NAME} | {INSTAGRAM_HANDLE}")
    st.stop() # Останавливаем выполнение, если не авторизован

# --- 4. БОКОВАЯ ПАНЕЛЬ (SIDEBAR) ---
with st.sidebar:
    st.title("🇰🇿 Методист PRO")
    
    # Блок ввода API ключа
    st.subheader("🔑 Настройки ИИ")
    user_key = st.text_input("Ваш Gemini API Key:", type="password", help="Введите ключ для работы нейросети")
    
    if user_key:
        try:
            genai.configure(api_key=user_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            st.success("API ключ активен")
        except:
            st.error("Неверный ключ")
            model = None
    else:
        st.warning("Введите API ключ!")
        st.caption("Получить бесплатно: aistudio.google.com")
        model = None

    st.divider()
    
    # Настройки материала
    t_fio = st.text_input("ФИО Учителя:", value="Учитель")
    prog = st.selectbox("Язык обучения:", [
        "Русский язык (Я1)", "Русский язык (Я2)", "Қазақ тілі (Т1)", "Қазақ тілі (Т2)",
        "Английский язык", "Математика", "Алгебра", "Геометрия", "Естествознание", "Биология", "История"
    ])
    
    st.subheader("Тип материала:")
    m_work = st.checkbox("Рабочий лист", value=True)
    m_sor = st.checkbox("БЖБ (СОР) / ТЖБ (СОЧ)")
    
    st.subheader("Компетенции:")
    m_func = st.checkbox("🧠 Функц. грамотность", value=True)
    m_pisa = st.checkbox("🌍 PISA / PIRLS")
    m_audit = st.checkbox("🎧 Аудирование")

    # --- БЛОК АВТОРА (ВАШИ ДАННЫЕ) ---
    st.divider()
    st.markdown(f"### 👩‍💻 Автор проекта")
    st.info(f"**{AUTHOR_NAME}**")
    
    # Кнопки соцсетей
    col_inst, col_wa = st.columns(2)
    with col_inst:
        st.markdown(f"[![Instagram](https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white)]({INSTAGRAM_URL})")
    with col_wa:
        st.markdown(f"[![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)]({WHATSAPP_URL})")
    
    st.caption(f"📞 Тел: {PHONE_NUMBER}")
    
    st.divider()
    if st.button("Выйти из системы", use_container_width=True):
        st.session_state['auth'] = False
        st.rerun()

# --- 5. ФУНКЦИИ ГЕНЕРАЦИИ WORD (Без изменений) ---
def clean_markdown(text):
    text = re.sub(r'[*_]{1,3}', '', text)
    text = re.sub(r'^#+\s*', '', text)
    return text.strip()

def create_worksheet(ai_text, title, subj, gr, teacher, max_score, is_sor, std_name=""):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    
    # Шапка
    doc_type = "БЖБ / СОР (Суммативное оценивание)" if is_sor else "Жұмыс парағы / Рабочий лист"
    header_table = doc.add_table(rows=2, cols=2)
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
    
    # Заголовок
    h = doc.add_heading(title.upper(), 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in h.runs: 
        run.font.name = 'Times New Roman'
        run.font.color.rgb = RGBColor(0,0,0)
        run.font.size = Pt(14)
        run.bold = True
    
    # Тело документа
    lines = ai_text.split('\n')
    table_data = []
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith('|'):
            if '---' in stripped_line: continue
            cells = [c.strip() for c in stripped_line.split('|') if c.strip()]
            if cells: table_data.append(cells)
            continue
        else:
            if table_data:
                tbl = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
                tbl.style = 'Table Grid'
                for i, row_cells in enumerate(table_data):
                    for j, cell_text in enumerate(row_cells):
                        cell = tbl.cell(i, j)
                        cell.text = clean_markdown(cell_text)
                table_data = []
                doc.add_paragraph()
            clean_line = clean_markdown(stripped_line)
            if not clean_line: continue
            p = doc.add_paragraph(clean_line)
            lower_line = clean_line.lower()
            if any(lower_line.startswith(s) for s in ["задание", "тапсырма", "task", "критерии", "дескриптор", "ответы", "ключи"]):
                p.bold = True
                
    doc.add_paragraph("\n" + "_"*45)
    footer = doc.add_paragraph()
    footer.add_run(f"Мұғалім: {teacher} ____________ (қолы)")
    
    # Подпись автора в документе
    doc.add_paragraph()
    copyright_run = doc.add_paragraph().add_run(f"Разработано: {AUTHOR_NAME} (@{INSTAGRAM_HANDLE})")
    copyright_run.font.size = Pt(8)
    copyright_run.font.color.rgb = RGBColor(128, 128, 128)
    
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 6. ОСНОВНОЙ ИНТЕРФЕЙС (ВКЛАДКИ) ---
st.header(f"Добро пожаловать, {t_fio}!")

tab1, tab2 = st.tabs(["👥 ВЕСЬ КЛАСС", "👤 РЕЗЕРВ (ИНКЛЮЗИЯ)"])

with tab1:
    if not model:
        st.info("⬅️ Пожалуйста, введите ваш API ключ в боковом меню слева.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            m_subj = st.text_input("Предмет:", key="ms", value="Русский язык")
            m_grade = st.selectbox("Класс:", [str(i) for i in range(1, 12)], index=4)
        with c2:
            m_sect = st.text_input("Раздел:", key="msc")
            m_topic = st.text_input("Тема урока:", key="mt")
        with c3:
            m_score = st.number_input("Макс. балл:", 1, 80, 10)
        
        m_goals = st.text_area("Цели обучения (ЦО) - вставьте из плана:", height=100, placeholder="Например: 5.1.2.1 Понимать значение слов...")

        if st.button("🚀 Создать материал", type="primary"):
            if not m_goals.strip():
                st.warning("Введите цели обучения.")
            else:
                prompt = f"""
                Ты методист. Создай материал: {m_topic}, {m_grade} класс. Цели: {m_goals}. 
                Предмет: {m_subj}. Тип: {'СОР/СОЧ' if m_sor else 'Рабочий лист'}.
                Добавь критерии оценивания и дескрипторы в виде таблицы.
                """
                with st.spinner("ИИ пишет задания и критерии..."):
                    try:
                        res = model.generate_content(prompt)
                        st.markdown("### Предпросмотр:")
                        st.markdown(res.text)
                        doc_file = create_worksheet(res.text, m_topic, m_subj, m_grade, t_fio, m_score, m_sor)
                        st.download_button(
                            label="💾 СКАЧАТЬ WORD (.docx)",
                            data=doc_file,
                            file_name=f"Worksheet_{m_topic}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                    except Exception as e:
                        st.error(f"Ошибка: {e}")

with tab2:
    st.write("Здесь будет функционал для адаптации (аналогично первой вкладке).")

# --- 7. ФУТЕР САЙТА (В самом низу) ---
st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; color: #666; padding: 10px;">
        <p style="margin-bottom: 5px;">Разработано с ❤️ для педагогов Казахстана</p>
        <p style="font-size: 0.9em;"><b>Автор: {AUTHOR_NAME}</b> | <a href="{INSTAGRAM_URL}" target="_blank">@{INSTAGRAM_HANDLE}</a></p>
    </div>
    """, 
    unsafe_allow_html=True
)
