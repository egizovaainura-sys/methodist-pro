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

# --- 2. СЛОВАРЬ ПЕРЕВОДОВ (ПОЛНЫЙ) ---
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
    "inc_diag": {"RU": "Диагноз/Особенности:", "KZ": "Диагноз/Ерекшеліктері:"},
    "func_lit": {"RU": "🧠 Функциональная грамотность (PISA)", "KZ": "🧠 Функционалдық сауаттылық (PISA)"},
    "btn_create": {"RU": "🚀 Создать материал", "KZ": "🚀 Материал жасау"},
    "download_btn": {"RU": "💾 СКАЧАТЬ WORD", "KZ": "💾 WORD ЖҮКТЕУ"},
    "preview": {"RU": "### Предпросмотр:", "KZ": "### Алдын ала қарау:"},
    "exit_btn": {"RU": "Выйти", "KZ": "Шығу"},
    "auth_title": {"RU": "Автор", "KZ": "Автор"}
}

# --- ПОЛНЫЕ СПИСКИ ПРЕДМЕТОВ ---
SUBJECTS_RU = [
    "Русский язык (Я1 - родной)", "Русский язык (Я2 - второй)", 
    "Казахский язык (Т1 - родной)", "Казахский язык (Т2 - второй)",
    "Литературное чтение", "Обучение грамоте", "Букварь", "Ана тілі",
    "Математика", "Алгебра", "Геометрия", 
    "Естествознание", "Познание мира", 
    "Физика", "Химия", "Биология", "География", "Информатика",
    "История Казахстана", "Всемирная история", 
    "Английский язык", 
    "Музыка", "Художественный труд", "Изобразительное искусство (Рисование)", "Физическая культура"
]

SUBJECTS_KZ = [
    "Орыс тілі (Я1 - орыс сыныптары)", "Орыс тілі (Я2 - қазақ сыныптары)", 
    "Қазақ тілі (Т1 - қазақ сыныптары)", "Қазақ тілі (Т2 - орыс сыныптары)",
    "Әдебиеттік оқу", "Сауат ашу", "Әліппе", "Ана тілі",
    "Математика", "Алгебра", "Геометрия", 
    "Жаратылыстану", "Дүниетану", 
    "Физика", "Химия", "Биология", "География", "Информатика",
    "Қазақстан тарихы", "Дүниежүзі тарихы", 
    "Ағылшын тілі", 
    "Музыка", "Көркем еңбек", "Бейнелеу өнері", "Дене шынықтыру"
]

def get_text(key, lang_code):
    return TRANS.get(key, {}).get(lang_code, key)

# --- 3. АВТОРИЗАЦИЯ И ИИ (ИСПРАВЛЕННЫЙ БЛОК) ---
def check_access(user_phone):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=st.secrets["gsheet_url"], ttl=0)
        clean_input = ''.join(filter(str.isdigit, str(user_phone)))
        allowed_phones = df.iloc[:, 1].astype(str).str.replace(r'\D', '', regex=True).tolist()
        return clean_input in allowed_phones
    except Exception: 
        return False

def configure_ai():
    """Функция настройки ИИ с подробной диагностикой ошибок"""
    if "GOOGLE_API_KEY" not in st.secrets:
        st.error("Ошибка: GOOGLE_API_KEY не найден в Secrets Streamlit!")
        return None
    
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # Пытаемся создать модель самым современным способом
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Тестовый микро-вызов для проверки на 404
        model.generate_content("test", generation_config={"max_output_tokens": 1})
        return model
    except Exception as e:
        st.error(f"⚠️ Ошибка инициализации ИИ: {e}")
        # Если 1.5-flash не пошла, пробуем резервную 1.0 Pro
        try:
            return genai.GenerativeModel('gemini-pro')
        except:
            return None

# --- 4. ЛОГИКА ВХОДА ---
if 'lang' not in st.session_state: st.session_state['lang'] = 'RU'
if 'auth' not in st.session_state: st.session_state['auth'] = False

with st.sidebar:
    lang_select = st.selectbox("🌐 Тіл / Язык", ["Русский", "Қазақша"], index=0 if st.session_state['lang']=='RU' else 1)
    st.session_state['lang'] = "RU" if lang_select == "Русский" else "KZ"
    current_lang = st.session_state['lang']

if not st.session_state['auth']:
    st.title(get_text("login_title", current_lang))
    st.markdown(get_text("login_prompt", current_lang))
    phone_input = st.text_input(get_text("phone_label", current_lang))
    if st.button(get_text("login_btn", current_lang)):
        with st.spinner("Проверка..."):
            if check_access(phone_input):
                st.session_state['auth'] = True
                st.rerun()
            else: st.error(get_text("access_denied", current_lang))
    st.stop()

# Инициализируем модель после авторизации
model = configure_ai()

# --- 5. БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.divider()
    st.success(get_text('status_active', current_lang))
    t_fio = st.text_input(get_text("teacher_fio", current_lang), value="Учитель")
    
    with st.expander("🛠 Диагностика"):
        if st.button("Список моделей"):
            try:
                ms = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                st.write(ms)
            except Exception as e:
                st.write(f"Ошибка списка: {e}")

    if st.button(get_text("exit_btn", current_lang)):
        st.session_state['auth'] = False
        st.rerun()

# --- 6. ФУНКЦИИ WORD (ПОЛНЫЙ КОД) ---
def clean_markdown(text):
    text = re.sub(r'[*_]{1,3}', '', text)
    text = re.sub(r'^#+\s*', '', text)
    return text.strip()

def create_docx(ai_text, title, subj, gr, teacher, lang_code, date_str, is_ksp=False, std_name=""):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(11)
    
    labels = {"RU": {"student": "Ученик", "subj": "Предмет", "class": "Класс", "date": "Дата"}, "KZ": {"student": "Оқушы", "subj": "Пән", "class": "Сынып", "date": "Күні"}}
    L = labels[lang_code]

    if not is_ksp:
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = f"{L['student']}: {std_name if std_name else '________________'}"
        table.cell(1, 0).text = f"{L['subj']}: {subj} | {L['class']}: {gr}"
        table.cell(0, 1).text = f"{L['date']}: {date_str}"
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
        stripped = line.strip()
        if stripped.startswith('|'):
            if '---' in stripped: continue
            cells = [c.strip() for c in stripped.split('|') if c.strip()]
            if cells: table_data.append(cells)
        else:
            if table_data:
                cols_count = len(table_data[0])
                tbl = doc.add_table(rows=len(table_data), cols=cols_count); tbl.style = 'Table Grid'
                for i, row in enumerate(table_data):
                    for j in range(min(len(row), cols_count)):
                        cell = tbl.cell(i, j); cell.text = clean_markdown(row[j])
                        if i == 0:
                            for p in cell.paragraphs:
                                for r in p.runs: r.font.bold = True
                table_data = []; doc.add_paragraph()
            clean_line = clean_markdown(stripped)
            if clean_line:
                p = doc.add_paragraph(clean_line)
                if any(clean_line.lower().startswith(x) for x in ["задание", "тапсырма", "критерии"]):
                    if p.runs: p.runs[0].bold = True

    buf = BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- 7. ОСНОВНОЙ ИНТЕРФЕЙС ---
st.title("🇰🇿 Methodist PRO")
sel_date = st.date_input(get_text("date_label", current_lang), datetime.date.today())
date_str = sel_date.strftime("%d.%m.%Y")

t1, t2, t3 = st.tabs([get_text("tab_class", current_lang), get_text("tab_inc", current_lang), get_text("tab_ksp", current_lang)])
subj_list = SUBJECTS_KZ if current_lang == "KZ" else SUBJECTS_RU

# ВКЛАДКА 1
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
        use_pisa = st.checkbox(get_text("func_lit", current_lang), key="t1_pisa")
    m_goals = st.text_area(get_text("goals_label", current_lang), height=100, key="t1_gl")

    if st.button(get_text("btn_create", current_lang), type="primary", key="btn_t1"):
        if model and m_goals.strip():
            with st.spinner("Генерация..."):
                try:
                    prompt = f"Ты методист. Напиши {m_type} для {m_grade} класса по предмету {m_subj}. Тема: {m_topic}. Цели: {m_goals}. Язык: {current_lang}."
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
                    doc = create_docx(res.text, m_topic, m_subj, m_grade, t_fio, current_lang, date_str)
                    st.download_button(get_text("download_btn", current_lang), doc, f"{m_topic}.docx")
                except Exception as e: st.error(f"Ошибка генерации: {e}")
        else: st.warning("Проверьте ввод целей или статус ИИ.")

# (Вкладки t2 и t3 остаются по аналогии с использованием объекта model)
# ... [Дальнейший код вкладок t2 и t3 с твоей логикой] ...

st.markdown("---")
st.markdown(f"<center>{AUTHOR_NAME} © 2026</center>", unsafe_allow_html=True)
