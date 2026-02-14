import streamlit as st
import google.generativeai as genai
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
from streamlit_gsheets import GSheetsConnection
import datetime

# --- 1. НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="Methodist PRO", layout="wide", page_icon="📚")

# --- ДАННЫЕ АВТОРА ---
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
    "status_active": {"RU": "✅ Подписка PRO активна", "KZ": "✅ PRO жазылым белсенді"},
    
    "teacher_fio": {"RU": "ФИО Учителя:", "KZ": "Мұғалімнің А.Т.Ә.:"},
    "date_label": {"RU": "Дата урока:", "KZ": "Сабақ күні:"},
    "subject_label": {"RU": "Предмет:", "KZ": "Пән:"},
    "grade_label": {"RU": "Класс:", "KZ": "Сынып:"},
    "topic_label": {"RU": "Тема урока:", "KZ": "Сабақтың тақырыбы:"},
    "score_label": {"RU": "Макс. балл:", "KZ": "Макс. ұпай:"},
    "goals_label": {"RU": "Цели обучения (ЦО):", "KZ": "Оқу мақсаттары (ОМ):"},
    "ksp_goals": {"RU": "Цели урока:", "KZ": "Сабақтың мақсаты:"},
    "mat_type": {"RU": "Тип материала:", "KZ": "Материал түрі:"},
    "type_work": {"RU": "Рабочий лист", "KZ": "Жұмыс парағы"},
    "type_sor": {"RU": "БЖБ (СОР) / ТЖБ (СОЧ)", "KZ": "БЖБ (СОР) / ТЖБ (СОЧ)"},
    
    "tab_class": {"RU": "📝 ЗАДАНИЯ (СОР/СОЧ)", "KZ": "📝 ТАПСЫРМАЛАР (БЖБ/ТЖБ)"},
    "tab_inc": {"RU": "👤 ИНКЛЮЗИЯ (Отдельно)", "KZ": "👤 ЕРЕКШЕ БІЛІМ (Жеке)"},
    "tab_ksp": {"RU": "📖 КСП (130 приказ)", "KZ": "📖 ҚМЖ (130-бұйрық)"},
    
    "inc_check": {"RU": "Есть ученик с ООП (Инклюзия)?", "KZ": "Ерекше білім беру қажеттілігі бар оқушы бар ма?"},
    "inc_diag": {"RU": "Диагноз/Особенности (для КСП):", "KZ": "Диагноз/Ерекшеліктері:"},
    
    "btn_create": {"RU": "🚀 Создать материал", "KZ": "🚀 Материал жасау"},
    "download_btn": {"RU": "💾 СКАЧАТЬ WORD", "KZ": "💾 WORD ЖҮКТЕУ"},
    "auth_title": {"RU": "Автор и разработчик", "KZ": "Автор және әзірлеуші"},
    "exit_btn": {"RU": "Выйти", "KZ": "Шығу"}
}

# --- СПИСКИ ПРЕДМЕТОВ (Добавлены новые) ---
SUBJECTS_RU = [
    "Русский язык", "Казахский язык", "Литературное чтение",
    "Обучение грамоте", "Букварь", "Ана тілі",
    "Математика", "Алгебра", "Геометрия", 
    "Естествознание", "Познание мира", 
    "Физика", "Химия", "Биология", "География", 
    "История Казахстана", "Всемирная история", 
    "Английский язык", "Начальные классы"
]

SUBJECTS_KZ = [
    "Орыс тілі", "Қазақ тілі", "Әдебиеттік оқу",
    "Сауат ашу", "Әліппе", "Ана тілі",
    "Математика", "Алгебра", "Геометрия", 
    "Жаратылыстану", "Дүниетану", 
    "Физика", "Химия", "Биология", "География", 
    "Қазақстан тарихы", "Дүниежүзі тарихы", 
    "Ағылшын тілі", "Бастауыш сынып"
]

def get_text(key, lang_code):
    return TRANS.get(key, {}).get(lang_code, key)

# --- 3. АВТОРИЗАЦИЯ И ИИ ---
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
        with st.spinner("Wait..."):
            if check_access(phone_input):
                st.session_state['auth'] = True
                st.rerun()
            else: st.error(get_text("access_denied", current_lang))
    st.stop()

model = configure_ai()

# --- 5. БОКОВАЯ ПАНЕЛЬ ---
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

def create_docx(ai_text, title, subj, gr, teacher, lang_code, date_str, is_ksp=False, std_name=""):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(11) # Чуть меньше шрифт для таблиц
    
    # Шапка
    labels = {
        "RU": {"student": "Ученик", "subj": "Предмет", "class": "Класс", "date": "Дата"},
        "KZ": {"student": "Оқушы", "subj": "Пән", "class": "Сынып", "date": "Күні"}
    }
    L = labels[lang_code]

    if not is_ksp:
        # Шапка для СОР/СОЧ/Листов
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = f"{L['student']}: {std_name if std_name else '________________'}"
        table.cell(1, 0).text = f"{L['subj']}: {subj} | {L['class']}: {gr}"
        table.cell(0, 1).text = f"{L['date']}: {date_str}"
        doc.add_paragraph()

    h = doc.add_heading(title.upper(), 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Контент
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
                # Создаем таблицу
                tbl = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
                tbl.style = 'Table Grid'
                for i, row in enumerate(table_data):
                    for j, val in enumerate(row):
                        cell = tbl.cell(i, j)
                        cell.text = clean_markdown(val)
                        # Если это КСП и включена инклюзия, и это колонка адаптации (обычно 4-я или 5-я), можно выделить цветом (опционально)
                table_data = []
                doc.add_paragraph()
            
            if stripped:
                p = doc.add_paragraph(clean_markdown(stripped))
                if any(stripped.lower().startswith(x) for x in ["задание", "тапсырма", "этап", "кезең", "критерии", "дескриптор"]):
                    p.bold = True
    
    doc.add_paragraph("\n" + "_"*30)
    doc.add_paragraph(f"{'Мұғалім' if lang_code=='KZ' else 'Учитель'}: {teacher}")
    doc.add_paragraph("Разработано в Methodist PRO")
    
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 7. ЦЕНТРАЛЬНАЯ ПАНЕЛЬ ---
st.title("🇰🇿 Methodist PRO")

# ВЫБОР ДАТЫ (Глобально для всех вкладок)
c_d1, c_d2 = st.columns([1, 4])
with c_d1:
    sel_date = st.date_input(get_text("date_label", current_lang), datetime.date.today())
    date_str = sel_date.strftime("%d.%m.%Y")

t1, t2, t3 = st.tabs([get_text("tab_class", current_lang), get_text("tab_inc", current_lang), get_text("tab_ksp", current_lang)])

subj_list = SUBJECTS_KZ if current_lang == "KZ" else SUBJECTS_RU

# === ВКЛАДКА 1: СОР / СОЧ / РАБОЧИЕ ЛИСТЫ ===
with t1:
    c1, c2, c3 = st.columns(3)
    with c1:
        m_subj = st.selectbox(get_text("subject_label", current_lang), subj_list, key="t1_s")
        m_grade = st.selectbox(get_text("grade_label", current_lang), [str(i) for i in range(1, 12)], key="t1_g")
    with c2:
        m_topic = st.text_input(get_text("topic_label", current_lang), key="t1_t")
        m_type = st.radio(get_text("mat_type", current_lang), [get_text("type_work", current_lang), get_text("type_sor", current_lang)], key="t1_type")
    with c3:
        m_score = st.number_input(get_text("score_label", current_lang), 1, 80, 10, key="t1_sc")
        
    m_goals = st.text_area(get_text("goals_label", current_lang), height=100, key="t1_gl")

    if st.button(get_text("btn_create", current_lang), type="primary", key="btn_t1"):
        if not m_goals.strip(): st.warning("No goals")
        else:
            lang_instr = "Пиши на КАЗАХСКОМ языке" if current_lang == "KZ" else "Пиши на РУССКОМ языке"
            prompt = f"""
            Ты методист. {lang_instr}.
            Создай: {m_type}. Предмет: {m_subj}. Класс: {m_grade}. Тема: {m_topic}.
            Цели: {m_goals}. Макс балл: {m_score}.
            
            СТРУКТУРА:
            1. Задания разного уровня.
            2. Таблица: "Критерии оценивания" и "Дескрипторы".
            3. Ответы.
            """
            with st.spinner("Generating..."):
                try:
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
                    doc = create_docx(res.text, m_topic, m_subj, m_grade, t_fio, current_lang, date_str, False)
                    st.download_button(get_text("download_btn", current_lang), doc, file_name=f"Task_{m_topic}.docx")
                except Exception as e: st.error(f"Error: {e}")

# === ВКЛАДКА 2: ИНКЛЮЗИЯ (ОТДЕЛЬНО) ===
with t2:
    st.info("Адаптация для особых образовательных потребностей (ООП)")
    ic1, ic2 = st.columns(2)
    with ic1:
        i_name = st.text_input("Имя ученика / Оқушының аты:", key="i_n")
        i_diag = st.text_input("Диагноз / Ерекшеліктері:", placeholder="Например: ЗПР, нарушение зрения", key="i_d")
    with ic2:
        i_topic = st.text_input("Тема (из первой вкладки):", value=m_topic, key="i_t")
        i_goals = st.text_area("Цели (упрощенные):", value=m_goals, height=100, key="i_g")

    if st.button("🧩 Адаптировать / Бейімдеу", type="primary", key="btn_t2"):
        if not i_goals: st.warning("No goals")
        else:
            lang_instr = "Пиши на КАЗАХСКОМ" if current_lang == "KZ" else "Пиши на РУССКОМ"
            prompt = f"""
            Ты дефектолог. {lang_instr}.
            Адаптируй задания по теме '{i_topic}' для ученика: {i_name}. Диагноз: {i_diag}.
            Цели: {i_goals}.
            Сделай задания проще. Увеличь шрифт в описании.
            Добавь таблицу оценивания.
            """
            with st.spinner("Adapting..."):
                try:
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
                    doc = create_docx(res.text, f"Inclusion_{i_name}", m_subj, m_grade, t_fio, current_lang, date_str, False, i_name)
                    st.download_button(get_text("download_btn", current_lang), doc, file_name=f"Inc_{i_name}.docx")
                except Exception as e: st.error(f"Error: {e}")

# === ВКЛАДКА 3: КСП (130 ПРИКАЗ + ИНКЛЮЗИЯ) ===
with t3:
    st.subheader(get_text("tab_ksp", current_lang))
    k1, k2 = st.columns(2)
    with k1:
        k_subj = st.selectbox(get_text("subject_label", current_lang), subj_list, key="k_s")
        k_grade = st.selectbox(get_text("grade_label", current_lang), [str(i) for i in range(1, 12)], key="k_g")
    with k2:
        k_topic = st.text_input(get_text("topic_label", current_lang), key="k_t")
        k_vals = st.text_input("Ценности / Құндылықтар:", value="Патриотизм", key="k_v")

    k_om = st.text_area(get_text("goals_label", current_lang), placeholder="Код (например 5.1.2.1)...", key="k_om")
    k_sm = st.text_area(get_text("ksp_goals", current_lang), placeholder="Все учащиеся смогут...", key="k_sm")
    
    # --- БЛОК ИНКЛЮЗИИ В КСП ---
    st.markdown("---")
    use_inc = st.checkbox(get_text("inc_check", current_lang), key="k_inc_check")
    k_inc_desc = ""
    if use_inc:
        k_inc_desc = st.text_input(get_text("inc_diag", current_lang), placeholder="Пример: Ученик А (ЗПР) - упрощенные задания", key="k_inc_input")

    if st.button(get_text("btn_create", current_lang), type="primary", key="btn_ksp"):
        if not k_om.strip(): st.warning("No goals")
        else:
            lang_instr = "Пиши на КАЗАХСКОМ" if current_lang == "KZ" else "Пиши на РУССКОМ"
            
            # Логика формирования промпта с инклюзией
            inc_instruction = ""
            inc_column = ""
            if use_inc:
                inc_instruction = f"В классе есть ученик с ООП: {k_inc_desc}. Для него ОБЯЗАТЕЛЬНО добавь отдельный столбец в таблицу с адаптированным заданием и дескриптором."
                inc_column = "| Адаптация для ООП (Инклюзия)"
            
            prompt = f"""
            Ты методист (Казахстан, приказ 130). {lang_instr}.
            Составь КСП. Предмет: {k_subj}. Класс: {k_grade}. Тема: {k_topic}.
            ЦО: {k_om}. Цели урока: {k_sm}. Ценности: {k_vals}.
            
            {inc_instruction}
            
            СТРУКТУРА ТАБЛИЦЫ (строго):
            Этап урока | Действия педагога | Действия ученика {inc_column} | Оценивание | Ресурсы
            
            Этапы:
            1. Начало (Орг. момент).
            2. Середина (Новая тема, Практика).
            3. Конец (Рефлексия).
            """
            with st.spinner("Generating Plan..."):
                try:
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
                    doc = create_docx(res.text, f"КСП_{k_topic}", k_subj, k_grade, t_fio, current_lang, date_str, True)
                    st.download_button(get_text("download_btn", current_lang), doc, file_name=f"KSP_{k_topic}.docx")
                except Exception as e: st.error(f"Error: {e}")

st.markdown("---")
st.markdown(f"<center><b>{AUTHOR_NAME}</b> © 2026 | {INSTAGRAM_HANDLE}</center>", unsafe_allow_html=True)
