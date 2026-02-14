import streamlit as st
import google.generativeai as genai
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
from streamlit_gsheets import GSheetsConnection

# --- 1. НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="Methodist PRO", layout="wide", page_icon="📚")

# --- ДАННЫЕ АВТОРА ---
AUTHOR_NAME = "Адильбаева Айнура Дуйшембековна"
INSTAGRAM_HANDLE = "uchitel_tdk"
INSTAGRAM_URL = f"https://instagram.com/{INSTAGRAM_HANDLE}"
WHATSAPP_URL = "https://wa.me/77776513022"
PHONE_NUMBER = "+7 (777) 651-30-22"

# --- 2. СЛОВАРЬ ПЕРЕВОДОВ (РУС / КАЗ) ---
TRANS = {
    "login_title": {"RU": "Вход в систему Методист PRO", "KZ": "Methodist PRO жүйесіне кіру"},
    "login_prompt": {"RU": "Введите ваш номер телефона для доступа.", "KZ": "Кіру үшін телефон нөміріңізді енгізіңіз."},
    "phone_label": {"RU": "Номер телефона (например, 87771234567):", "KZ": "Телефон нөмірі (мысалы, 87771234567):"},
    "login_btn": {"RU": "Войти", "KZ": "Кіру"},
    "access_denied": {"RU": "Доступ закрыт. Номер не найден.", "KZ": "Кіруге тыйым салынды. Нөмір табылмады."},
    "buy_sub": {"RU": "Купить доступ у автора:", "KZ": "Жазылым сатып алу:"},
    
    "sidebar_settings": {"RU": "Настройки", "KZ": "Баптаулар"},
    "ai_key_label": {"RU": "Ваш Gemini API Key:", "KZ": "Сіздің Gemini API кілтіңіз:"},
    "ai_key_help": {"RU": "Введите ключ для работы нейросети", "KZ": "Нейрожүйе жұмыс істеуі үшін кілтті енгізіңіз"},
    "teacher_fio": {"RU": "ФИО Учителя:", "KZ": "Мұғалімнің А.Т.Ә.:"},
    "subject_label": {"RU": "Предмет:", "KZ": "Пән:"},
    "grade_label": {"RU": "Класс:", "KZ": "Сынып:"},
    "topic_label": {"RU": "Тема урока:", "KZ": "Сабақтың тақырыбы:"},
    "score_label": {"RU": "Макс. балл:", "KZ": "Макс. ұпай:"},
    "goals_label": {"RU": "Цели обучения:", "KZ": "Оқу мақсаттары:"},
    
    "mat_type": {"RU": "Тип материала:", "KZ": "Материал түрі:"},
    "type_work": {"RU": "Рабочий лист", "KZ": "Жұмыс парағы"},
    "type_sor": {"RU": "БЖБ (СОР) / ТЖБ (СОЧ)", "KZ": "БЖБ (СОР) / ТЖБ (СОЧ)"},
    
    "btn_create": {"RU": "🚀 Создать материал", "KZ": "🚀 Материал жасау"},
    "download_btn": {"RU": "💾 СКАЧАТЬ WORD", "KZ": "💾 WORD ЖҮКТЕУ"},
    "preview": {"RU": "### Предпросмотр:", "KZ": "### Алдын ала қарау:"},
    "auth_title": {"RU": "Автор и разработчик", "KZ": "Автор және әзірлеуші"},
    "exit_btn": {"RU": "Выйти", "KZ": "Шығу"}
}

# --- ОБНОВЛЕННЫЕ СПИСКИ ПРЕДМЕТОВ ---
SUBJECTS_RU = [
    "Русский язык (Я1 - для русских классов)", 
    "Русский язык (Я2 - для казахских классов)", 
    "Казахский язык (Т1 - для казахских классов)", 
    "Казахский язык (Т2 - для русских классов)",
    "Математика", "Алгебра", "Геометрия", "Физика", "Химия", "Биология", 
    "История Казахстана", "Всемирная история", "География", "Английский язык", "Начальные классы"
]

SUBJECTS_KZ = [
    "Орыс тілі (Я1 - орыс сыныптары үшін)", 
    "Орыс тілі (Я2 - қазақ сыныптары үшін)", 
    "Қазақ тілі (Т1 - қазақ сыныптары үшін)", 
    "Қазақ тілі (Т2 - орыс сыныптары үшін)",
    "Математика", "Алгебра", "Геометрия", "Физика", "Химия", "Биология", 
    "Қазақстан тарихы", "Дүниежүзі тарихы", "География", "Ағылшын тілі", "Бастауыш сынып"
]

def get_text(key, lang_code):
    return TRANS.get(key, {}).get(lang_code, key)

# --- 3. АВТОРИЗАЦИЯ ---
def check_access(user_phone):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=st.secrets["gsheet_url"], ttl=0)
        clean_input = ''.join(filter(str.isdigit, str(user_phone)))
        allowed_phones = df.iloc[:, 1].astype(str).str.replace(r'\D', '', regex=True).tolist()
        return clean_input in allowed_phones
    except Exception as e:
        st.error(f"Ошибка проверки базы: {e}")
        return False

# --- 4. ЛОГИКА ВХОДА ---
if 'lang' not in st.session_state:
    st.session_state['lang'] = 'RU'

with st.sidebar:
    lang_select = st.selectbox("🌐 Тіл / Язык", ["Русский", "Қазақша"], index=0 if st.session_state['lang']=='RU' else 1)
    st.session_state['lang'] = "RU" if lang_select == "Русский" else "KZ"
    current_lang = st.session_state['lang']

if 'auth' not in st.session_state:
    st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title(get_text("login_title", current_lang))
    st.markdown(get_text("login_prompt", current_lang))
    
    phone = st.text_input(get_text("phone_label", current_lang))
    
    if st.button(get_text("login_btn", current_lang)):
        with st.spinner("Проверка... / Тексеру..."):
            if check_access(phone):
                st.session_state['auth'] = True
                st.success("OK!")
                st.rerun()
            else:
                st.error(get_text("access_denied", current_lang))
                st.info(f"{get_text('buy_sub', current_lang)} {AUTHOR_NAME}")
                st.markdown(f"[WhatsApp]({WHATSAPP_URL})")
    
    st.divider()
    st.caption(f"Dev: {AUTHOR_NAME} | {INSTAGRAM_HANDLE}")
    st.stop()

# --- 5. ОСНОВНОЕ ПРИЛОЖЕНИЕ ---

with st.sidebar:
    st.divider()
    st.subheader("🔑 AI Key")
    user_key = st.text_input(get_text("ai_key_label", current_lang), type="password", help=get_text("ai_key_help", current_lang))
    
    if user_key:
        try:
            genai.configure(api_key=user_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            st.success("API Key Active")
        except:
            model = None
    else:
        st.warning("API Key required!")

    st.divider()
    t_fio = st.text_input(get_text("teacher_fio", current_lang), value="Teacher")
    
    st.subheader(get_text("mat_type", current_lang))
    m_work = st.checkbox(get_text("type_work", current_lang), value=True)
    m_sor = st.checkbox(get_text("type_sor", current_lang))

    st.divider()
    st.markdown(f"### 👩‍💻 {get_text('auth_title', current_lang)}")
    st.info(f"**{AUTHOR_NAME}**")
    
    col_inst, col_wa = st.columns(2)
    with col_inst:
        st.markdown(f"[![Instagram](https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white)]({INSTAGRAM_URL})")
    with col_wa:
        st.markdown(f"[![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)]({WHATSAPP_URL})")
    st.caption(f"📞 {PHONE_NUMBER}")
    
    st.divider()
    if st.button(get_text("exit_btn", current_lang), use_container_width=True):
        st.session_state['auth'] = False
        st.rerun()

# --- ФУНКЦИИ WORD ---
def clean_markdown(text):
    text = re.sub(r'[*_]{1,3}', '', text)
    text = re.sub(r'^#+\s*', '', text)
    return text.strip()

def create_worksheet(ai_text, title, subj, gr, teacher, max_score, is_sor, lang_code, std_name=""):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    
    labels = {
        "RU": {"student": "Оқушы / Ученик", "subj": "Предмет", "class": "Класс", "date": "Дата", "mark": "Оценка", "score": "Балл"},
        "KZ": {"student": "Оқушы", "subj": "Пән", "class": "Сынып", "date": "Күні", "mark": "Баға", "score": "Балл"}
    }
    L = labels[lang_code]
    doc_type = "БЖБ / СОР" if is_sor else ("Жұмыс парағы" if lang_code == "KZ" else "Рабочий лист")
    
    header_table = doc.add_table(rows=2, cols=2)
    header_table.cell(0, 0).text = f"{L['student']}: {std_name if std_name else '____________________'}"
    header_table.cell(1, 0).text = f"{L['subj']}: {subj} | {L['class']}: {gr}"
    date_cell = header_table.cell(0, 1)
    date_cell.text = f"{L['date']}: ____.____.202__"
    date_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    score_text = f"{L['score']}: ___ / {max_score}" if is_sor else f"{L['mark']}: _____"
    type_cell = header_table.cell(1, 1)
    type_cell.text = f"{doc_type}\n{score_text}"
    type_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    doc.add_paragraph()
    h = doc.add_heading(title.upper(), 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in h.runs: 
        run.font.name = 'Times New Roman'
        run.font.color.rgb = RGBColor(0,0,0)
        run.font.size = Pt(14)
        run.bold = True
    
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
            keywords = ["задание", "тапсырма", "task", "критерии", "дескриптор", "ответы", "ключи", "жауаптар"]
            if any(clean_line.lower().startswith(s) for s in keywords):
                p.bold = True
                
    doc.add_paragraph("\n" + "_"*45)
    doc.add_paragraph().add_run(f"{'Мұғалім' if lang_code=='KZ' else 'Учитель'}: {teacher} ____________")
    doc.add_paragraph().add_run(f"Author: {AUTHOR_NAME} (@{INSTAGRAM_HANDLE})").font.size = Pt(8)
    
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- ГЛАВНЫЙ ЭКРАН ---
st.title("🇰🇿 Methodist PRO")

if not model:
    st.info("⬅️ API Key required (Sidebar)")
else:
    c1, c2, c3 = st.columns(3)
    with c1:
        # Здесь меняется список предметов
        subj_list = SUBJECTS_KZ if current_lang == "KZ" else SUBJECTS_RU
        m_subj = st.selectbox(get_text("subject_label", current_lang), subj_list)
        m_grade = st.selectbox(get_text("grade_label", current_lang), [str(i) for i in range(1, 12)], index=4)
    with c2:
        m_topic = st.text_input(get_text("topic_label", current_lang))
    with c3:
        m_score = st.number_input(get_text("score_label", current_lang), 1, 80, 10)
    
    m_goals = st.text_area(get_text("goals_label", current_lang), height=100)

    if st.button(get_text("btn_create", current_lang), type="primary"):
        if not m_goals.strip():
            st.warning("Error: No Goals")
        else:
            # Умный промпт: передаем выбранный предмет (m_subj), и ИИ сам поймет Я1 это или Я2
            if current_lang == "KZ":
                prompt = f"Сен Қазақстанның әдіскерісің. Бұл материалды ТЕК ҚАЗАҚ ТІЛІНДЕ жаз. Пән: {m_subj}. Тақырып: {m_topic}. Сынып: {m_grade}. Мақсаттар: {m_goals}. Түрі: {'БЖБ/СОР' if m_sor else 'Жұмыс парағы'}. Міндетті түрде 'Бағалау критерийлері', 'Дескриптор' және 'Жауаптар' қос."
            else:
                prompt = f"Ты методист. Напиши материал на РУССКОМ языке. Предмет: {m_subj}. Тема: {m_topic}. Класс: {m_grade}. Цели: {m_goals}. Тип: {'СОР/СОЧ' if m_sor else 'Рабочий лист'}. Обязательно добавь 'Критерии оценивания', 'Дескрипторы' и 'Ответы'."
            
            with st.spinner("Wait..."):
                try:
                    res = model.generate_content(prompt)
                    st.markdown(get_text("preview", current_lang))
                    st.markdown(res.text)
                    doc_file = create_worksheet(res.text, m_topic, m_subj, m_grade, t_fio, m_score, m_sor, current_lang)
                    st.download_button(get_text("download_btn", current_lang), doc_file, file_name=f"Methodist_{m_topic}.docx")
                except Exception as e:
                    st.error(f"Error: {e}")

# Футер
st.markdown("---")
st.markdown(f"<div style='text-align: center; color: #666;'>Created by: <b>{AUTHOR_NAME}</b> | @{INSTAGRAM_HANDLE}</div>", unsafe_allow_html=True)
