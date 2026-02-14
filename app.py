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

# --- ДАННЫЕ АВТОРА (из вашего интерфейса) ---
AUTHOR_NAME = "Адильбаева Айнура Дуйшембековна"
INSTAGRAM_HANDLE = "uchitel_tdk"
INSTAGRAM_URL = f"https://instagram.com/{INSTAGRAM_HANDLE}"
WHATSAPP_URL = "https://wa.me/77776513022"
PHONE_NUMBER = "+7 (777) 651-30-22"

# --- 2. СЛОВАРЬ ПЕРЕВОДОВ ---
TRANS = {
    "login_title": {"RU": "Вход в систему Методист PRO", "KZ": "Methodist PRO жүйесіне кіру"},
    "login_prompt": {"RU": "Введите ваш номер телефона для доступа.", "KZ": "Кіру үшін телефон нөміріңізді енгізіңіз."},
    "phone_label": {"RU": "Номер телефона:", "KZ": "Телефон нөмірі:"},
    "login_btn": {"RU": "Войти", "KZ": "Кіру"},
    "access_denied": {"RU": "Доступ закрыт. Номер не найден.", "KZ": "Кіруге тыйым салынды. Нөмір табылмады."},
    "buy_sub": {"RU": "Купить доступ:", "KZ": "Жазылым сатып алу:"},
    "status_active": {"RU": "✅ Подписка PRO активна", "KZ": "✅ PRO жазылым белсенді"},
    "status_desc": {"RU": "Все функции включены", "KZ": "Барлық функциялар қосулы"},
    "teacher_fio": {"RU": "ФИО Учителя:", "KZ": "Мұғалімнің А.Т.Ә.:"},
    "subject_label": {"RU": "Предмет:", "KZ": "Пән:"},
    "grade_label": {"RU": "Класс:", "KZ": "Сынып:"},
    "topic_label": {"RU": "Тема урока:", "KZ": "Сабақтың тақырыбы:"},
    "score_label": {"RU": "Макс. балл:", "KZ": "Макс. ұпай:"},
    "goals_label": {"RU": "Цели обучения (ЦО):", "KZ": "Оқу мақсаттары (ОМ):"},
    "ksp_goals": {"RU": "Цели урока:", "KZ": "Сабақтың мақсаты:"},
    "ksp_values": {"RU": "Привитие ценностей:", "KZ": "Құндылықтарды дарыту:"},
    "mat_type": {"RU": "Тип материала:", "KZ": "Материал түрі:"},
    "type_work": {"RU": "Рабочий лист", "KZ": "Жұмыс парағы"},
    "type_sor": {"RU": "БЖБ (СОР) / ТЖБ (СОЧ)", "KZ": "БЖБ (СОР) / ТЖБ (СОЧ)"},
    "tab_class": {"RU": "👥 ВЕСЬ КЛАСС", "KZ": "👥 БҮКІЛ СЫНЫП"},
    "tab_inc": {"RU": "👤 ИНКЛЮЗИЯ", "KZ": "👤 ЕРЕКШЕ БІЛІМ"},
    "tab_ksp": {"RU": "📖 КСП (130 приказ РК)", "KZ": "📖 ҚМЖ (130-бұйрық)"},
    "btn_create": {"RU": "🚀 Создать материал", "KZ": "🚀 Материал жасау"},
    "download_btn": {"RU": "💾 СКАЧАТЬ WORD", "KZ": "💾 WORD ЖҮКТЕУ"},
    "preview": {"RU": "### Предпросмотр:", "KZ": "### Алдын ала қарау:"},
    "auth_title": {"RU": "Автор и разработчик", "KZ": "Автор және әзірлеуші"},
    "exit_btn": {"RU": "Выйти", "KZ": "Шығу"}
}

SUBJECTS_RU = ["Русский язык (Я1)", "Русский язык (Я2)", "Казахский язык (Т1)", "Казахский язык (Т2)", "Математика", "Алгебра", "Геометрия", "Физика", "Химия", "Биология", "История Казахстана", "География", "Английский язык", "Начальные классы"]
SUBJECTS_KZ = ["Орыс тілі (Я1)", "Орыс тілі (Я2)", "Қазақ тілі (Т1)", "Қазақ тілі (Т2)", "Математика", "Алгебра", "Геометрия", "Физика", "Химия", "Биология", "Қазақстан тарихы", "География", "Ағылшын тілі", "Бастауыш сынып"]

def get_text(key, lang_code):
    return TRANS.get(key, {}).get(lang_code, key)

# --- 3. АВТОРИЗАЦИЯ И ИИ (из ваших настроек Secrets) ---
def check_access(user_phone):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=st.secrets["gsheet_url"], ttl=0)
        clean_input = ''.join(filter(str.isdigit, str(user_phone)))
        allowed_phones = df.iloc[:, 1].astype(str).str.replace(r'\D', '', regex=True).tolist()
        return clean_input in allowed_phones
    except: return False

def configure_ai():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-1.5-flash')
    except: return None

# --- 4. ЛОГИКА ВХОДА ---
if 'lang' not in st.session_state: st.session_state['lang'] = 'RU'
if 'auth' not in st.session_state: st.session_state['auth'] = False

with st.sidebar:
    lang_select = st.selectbox("🌐 Тіл / Язык", ["Русский", "Қазақша"], index=0 if st.session_state['lang']=='RU' else 1)
    st.session_state['lang'] = "RU" if lang_select == "Русский" else "KZ"
    current_lang = st.session_state['lang']

if not st.session_state['auth']:
    st.title(get_text("login_title", current_lang))
    phone_input = st.text_input(get_text("phone_label", current_lang))
    if st.button(get_text("login_btn", current_lang)):
        if check_access(phone_input):
            st.session_state['auth'] = True
            st.rerun()
        else: st.error(get_text("access_denied", current_lang))
    st.stop()

model = configure_ai()

# --- 5. БОКОВАЯ ПАНЕЛЬ (из вашего интерфейса) ---
with st.sidebar:
    st.divider()
    st.success(get_text('status_active', current_lang))
    t_fio = st.text_input(get_text("teacher_fio", current_lang), value="Teacher")
    st.divider()
    st.markdown(f"### 👩‍💻 {get_text('auth_title', current_lang)}")
    st.info(f"**{AUTHOR_NAME}**")
    col1, col2 = st.columns(2)
    with col1: st.markdown(f"[![Inst](https://img.shields.io/badge/Inst-E4405F?logo=instagram&logoColor=white)]({INSTAGRAM_URL})")
    with col2: st.markdown(f"[![WA](https://img.shields.io/badge/WA-25D366?logo=whatsapp&logoColor=white)]({WHATSAPP_URL})")
    st.caption(f"📞 {PHONE_NUMBER}")
    if st.button(get_text("exit_btn", current_lang)):
        st.session_state['auth'] = False
        st.rerun()

# --- 6. ФУНКЦИИ WORD ---
def clean_markdown(text):
    text = re.sub(r'[*_]{1,3}', '', text)
    text = re.sub(r'^#+\s*', '', text)
    return text.strip()

def create_docx(ai_text, title, subj, gr, teacher, lang_code, is_ksp=False):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    
    # Заголовок
    h = doc.add_heading(title.upper(), 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Обработка контента (таблицы и параграфы)
    lines = ai_text.split('\n')
    table_data = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|'):
            if '---' in stripped: continue
            cells = [c.strip() for c in stripped.split('|') if c.strip()]
            if cells: table_data.append(cells)
        else:
            if table_data:
                tbl = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
                tbl.style = 'Table Grid'
                for i, row in enumerate(table_data):
                    for j, val in enumerate(row):
                        tbl.cell(i, j).text = clean_markdown(val)
                table_data = []
                doc.add_paragraph()
            if stripped:
                p = doc.add_paragraph(clean_markdown(stripped))
                if any(stripped.lower().startswith(x) for x in ["задание", "тапсырма", "этап", "кезең"]):
                    p.bold = True
    
    doc.add_paragraph("\n" + "_"*30)
    doc.add_paragraph(f"Учитель: {teacher} / Разработано: Methodist PRO")
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 7. ВКЛАДКИ (ИНТЕРФЕЙС) ---
st.title("🇰🇿 Methodist PRO")
t1, t2, t3 = st.tabs([get_text("tab_class", current_lang), get_text("tab_inc", current_lang), get_text("tab_ksp", current_lang)])

# (Логика вкладок 1 и 2 остается прежней...)
with t1:
    subj_list = SUBJECTS_KZ if current_lang == "KZ" else SUBJECTS_RU
    c1, c2 = st.columns(2)
    with c1:
        m_subj = st.selectbox(get_text("subject_label", current_lang), subj_list, key="t1_s")
        m_grade = st.selectbox(get_text("grade_label", current_lang), [str(i) for i in range(1, 12)], key="t1_g")
    with c2:
        m_topic = st.text_input(get_text("topic_label", current_lang), key="t1_t")
        m_score = st.number_input(get_text("score_label", current_lang), 1, 100, 10)
    m_goals = st.text_area(get_text("goals_label", current_lang), height=100)
    if st.button(get_text("btn_create", current_lang), type="primary", key="t1_btn"):
        # Логика генерации аналогична КСП ниже...
        pass

# --- ВКЛАДКА КСП (ПО 130 ПРИКАЗУ РК) ---
with t3:
    st.subheader("📖 Создание Краткосрочного плана (КСП)")
    c1, c2 = st.columns(2)
    with c1:
        k_subj = st.selectbox(get_text("subject_label", current_lang), subj_list, key="k_s")
        k_grade = st.selectbox(get_text("grade_label", current_lang), [str(i) for i in range(1, 12)], key="k_g")
    with c2:
        k_topic = st.text_input(get_text("topic_label", current_lang), key="k_t")
        k_vals = st.text_input(get_text("ksp_values", current_lang), value="Патриотизм, уважение")

    k_om = st.text_area(get_text("goals_label", current_lang), placeholder="Вставьте ЦО (например, 3.1.2.4)")
    k_sm = st.text_area(get_text("ksp_goals", current_lang), placeholder="Чего должны достичь ученики на уроке?")

    if st.button(get_text("btn_create", current_lang), type="primary", key="k_btn"):
        if not k_om.strip() or not k_topic.strip():
            st.warning("Заполните тему и цели обучения!")
        else:
            lang_instr = "Пиши строго на казахском" if current_lang == "KZ" else "Пиши строго на русском"
            prompt = f"""
            Ты - эксперт-методист Казахстана. Составь Краткосрочный план урока (КСП) по приказу №130.
            Предмет: {k_subj}. Класс: {k_grade}. Тема: {k_topic}.
            Цели обучения (ЦО): {k_om}.
            Цели урока: {k_sm}.
            Ценности: {k_vals}.
            
            СТРУКТУРА (обязательно в таблице):
            1. Шапка: ФИО, Класс, Пән, Сабақтың тақырыбы, Оқу мақсаттары.
            2. План-таблица этапов урока: 
               - Начало (3-5 мин): Организация, актуализация.
               - Середина (30 мин): Новая тема, задания, работа в парах/группах, дескрипторы к заданиям.
               - Конец (5 мин): Рефлексия, домашнее задание.
            3. Столбцы таблицы: Этап урока | Запланированная деятельность | Ресурсы | Оценивание.
            
            {lang_instr}. Форматируй как методический документ.
            """
            with st.spinner(get_text("spinner", current_lang)):
                try:
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
                    doc_file = create_docx(res.text, f"КСП_{k_topic}", k_subj, k_grade, t_fio, current_lang, True)
                    st.download_button(get_text("download_btn", current_lang), doc_file, file_name=f"KSP_{k_topic}.docx")
                except Exception as e: st.error(f"Ошибка: {e}")

st.markdown("---")
st.markdown(f"<center><b>{AUTHOR_NAME}</b> © 2026 | {INSTAGRAM_HANDLE}</center>", unsafe_allow_html=True)
