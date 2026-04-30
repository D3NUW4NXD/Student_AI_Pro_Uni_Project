# =========================================================
# STUDENT AI PRO - FULLY WORKING VERSION
# =========================================================

import os
import streamlit as st
import sqlite3
import bcrypt
import uuid
from dotenv import load_dotenv
from groq import Groq
from duckduckgo_search import DDGS
import speech_recognition as sr
from PIL import Image
import pytesseract
import PyPDF2
import re
from datetime import datetime

# ---------------- CONFIG ----------------
load_dotenv()

st.set_page_config(
    page_title="Student AI Pro",
    page_icon="🎓",
    layout="wide"
)

# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0B1120 0%, #0F172A 100%);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #020617 0%, #0B1120 100%);
        border-right: 1px solid rgba(37, 99, 235, 0.2);
    }
    
    [data-testid="stSidebar"] .stButton button {
        background: #1E293B;
        border: 1px solid #334155;
        color: white;
        border-radius: 10px;
        width: 100%;
    }
    
    [data-testid="stSidebar"] .stButton button:hover {
        background: #2563EB;
    }
    
    /* Hide default elements */
    #MainMenu, footer, header {
        display: none !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1E293B;
    }
    ::-webkit-scrollbar-thumb {
        background: #3B4A5F;
        border-radius: 10px;
    }
    
    /* Make messages wider horizontally */
    .user-bubble, .assistant-bubble {
        max-width: 85% !important;
        min-width: 200px;
    }
    
    /* Bottom bar styling */
    .bottom-bar {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: #0F172A;
        padding: 16px 20px;
        border-top: 1px solid #334155;
        z-index: 999;
    }
    
    .main .block-container {
        padding-bottom: 100px !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect("chat.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password BLOB)")
    
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chats'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        conn.execute("CREATE TABLE chats(chat_id TEXT PRIMARY KEY, user TEXT, title TEXT)")
    
    conn.execute("CREATE TABLE IF NOT EXISTS messages(chat_id TEXT, role TEXT, content TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS memory(user TEXT, key TEXT, value TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS chat_memory(chat_id TEXT PRIMARY KEY, summary TEXT)")
    conn.commit()
    conn.close()

def create_user(u, p):
    conn = sqlite3.connect("chat.db")
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute("SELECT username FROM users WHERE username = ?", (u,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        conn.close()
        return False, "Username already exists"
    
    # Create new user
    hashed = bcrypt.hashpw(p.encode(), bcrypt.gensalt())
    try:
        cursor.execute("INSERT INTO users(username, password) VALUES(?,?)", (u, hashed))
        conn.commit()
        conn.close()
        return True, "User created successfully"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Username already exists"
    except Exception as e:
        conn.close()
        return False, f"Error: {str(e)}"

def check_user(u, p):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username=?", (u,))
    row = cur.fetchone()
    conn.close()
    return row and bcrypt.checkpw(p.encode(), row[0])

def create_chat(cid, user, title="New Chat"):
    conn = sqlite3.connect("chat.db")
    try:
        conn.execute("INSERT OR IGNORE INTO chats(chat_id, user, title) VALUES(?,?,?)", 
                     (cid, user, title))
    except sqlite3.OperationalError as e:
        if "table chats has 4 columns" in str(e):
            try:
                conn.execute("INSERT OR IGNORE INTO chats(chat_id, user, title, created_at) VALUES(?,?,?,?)",
                           (cid, user, title, datetime.now().isoformat()))
            except:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(chats)")
                columns = [col[1] for col in cursor.fetchall()]
                placeholders = ','.join(['?'] * len(columns))
                col_names = ','.join(columns)
                values = []
                for col in columns:
                    if col == 'chat_id':
                        values.append(cid)
                    elif col == 'user':
                        values.append(user)
                    elif col == 'title':
                        values.append(title)
                    elif col == 'created_at':
                        values.append(datetime.now().isoformat())
                    else:
                        values.append(None)
                conn.execute(f"INSERT OR IGNORE INTO chats({col_names}) VALUES({placeholders})", values)
        else:
            raise
    conn.commit()
    conn.close()

def get_chats(user):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()
    try:
        cur.execute("SELECT chat_id, title FROM chats WHERE user=?", (user,))
        rows = cur.fetchall()
    except:
        cur.execute("SELECT * FROM chats WHERE user=?", (user,))
        rows = [(row[0], row[2] if len(row) > 2 else "Chat") for row in cur.fetchall()]
    conn.close()
    return rows

def rename_chat(cid, title):
    conn = sqlite3.connect("chat.db")
    conn.execute("UPDATE chats SET title=? WHERE chat_id=?", (title, cid))
    conn.commit()
    conn.close()

def delete_chat(cid):
    conn = sqlite3.connect("chat.db")
    conn.execute("DELETE FROM chats WHERE chat_id=?", (cid,))
    conn.execute("DELETE FROM messages WHERE chat_id=?", (cid,))
    conn.execute("DELETE FROM chat_memory WHERE chat_id=?", (cid,))
    conn.commit()
    conn.close()

def save_message(cid, role, msg):
    conn = sqlite3.connect("chat.db")
    conn.execute("INSERT INTO messages(chat_id, role, content) VALUES(?,?,?)", (cid, role, msg))
    conn.commit()
    conn.close()

def load_messages(cid):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()
    cur.execute("SELECT role, content FROM messages WHERE chat_id=?", (cid,))
    rows = cur.fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in rows]

def save_memory(user, key, value):
    conn = sqlite3.connect("chat.db")
    conn.execute("DELETE FROM memory WHERE user=? AND key=?", (user, key))
    conn.execute("INSERT INTO memory VALUES(?,?,?)", (user, key, value))
    conn.commit()
    conn.close()

def load_memory(user):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM memory WHERE user=?", (user,))
    rows = cur.fetchall()
    conn.close()
    return {k: v for k, v in rows}

def save_chat_memory(chat_id, summary):
    conn = sqlite3.connect("chat.db")
    conn.execute("INSERT OR REPLACE INTO chat_memory VALUES(?,?)", (chat_id, summary))
    conn.commit()
    conn.close()

def load_chat_memory(chat_id):
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()
    cur.execute("SELECT summary FROM chat_memory WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else ""

def needs_search(q):
    keywords = ["latest", "today", "news", "price", "weather", "current"]
    return any(k in q.lower() for k in keywords)

def search_web(q):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(q, max_results=2))
            if results:
                return "\n\n".join([f"• {r['body'][:300]}" for r in results])
    except:
        pass
    return ""

def listen():
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            st.toast("🎤 Listening...")
            audio = r.listen(source, timeout=5, phrase_time_limit=8)
            text = r.recognize_google(audio)
            st.toast(f"Recognized: {text}")
            return text
    except:
        return ""

def read_pdf(file):
    try:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages[:5]:
            text += page.extract_text() or ""
        return text[:3000]
    except:
        return ""

def read_txt(file):
    try:
        return file.read().decode("utf-8", errors="ignore")[:3000]
    except:
        return ""

def read_image(file):
    try:
        img = Image.open(file)
        return pytesseract.image_to_string(img)[:2000]
    except:
        return ""

# ---------------- INIT ----------------
init_db()

try:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    MODEL = "llama-3.3-70b-versatile"
except:
    st.error("⚠️ Groq API key not found")
    st.stop()

PERSONAS = {
    "Tutor": "📘 Academic Tutor",
    "Assistant": "🤖 General Assistant",
    "Creative": "🎨 Creative Thinker",
    "Exam Coach": "🎯 Exam Specialist"
}

# ---------------- SESSION STATE ----------------
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "persona" not in st.session_state:
    st.session_state.persona = "Tutor"
if "file_text" not in st.session_state:
    st.session_state.file_text = ""
if "file_name" not in st.session_state:
    st.session_state.file_name = None
if "voice_input" not in st.session_state:
    st.session_state.voice_input = None
if "show_delete_confirm" not in st.session_state:
    st.session_state.show_delete_confirm = None
if "show_edit_confirm" not in st.session_state:
    st.session_state.show_edit_confirm = None

# ---------------- LOGIN ----------------
if not st.session_state.user:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="background: #020617; padding: 2rem; border-radius: 20px; border: 1px solid #2563EB;">
        <h2 style="text-align: center; color: white;">🎓 Student AI Pro</h2>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            u = st.text_input("Username", key="login_username")
            p = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", use_container_width=True, key="login_btn"):
                if check_user(u, p):
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")
        
        with tab2:
            reg_user = st.text_input("Username", key="reg_username")
            reg_pass = st.text_input("Password", type="password", key="reg_password")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
            
            if st.button("Register", use_container_width=True, key="register_btn"):
                if not reg_user or not reg_pass:
                    st.error("❌ Username and password required")
                elif reg_pass != reg_confirm:
                    st.error("❌ Passwords do not match")
                elif len(reg_pass) < 4:
                    st.error("❌ Password must be at least 4 characters")
                else:
                    success, message = create_user(reg_user, reg_pass)
                    if success:
                        st.success("✅ Account created successfully! Please login.")
                    else:
                        st.error(f"❌ {message}")
        
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ---------------- INIT CHAT ----------------
if not st.session_state.chat_id:
    st.session_state.chat_id = str(uuid.uuid4())
    create_chat(st.session_state.chat_id, st.session_state.user)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user}")
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())
        create_chat(st.session_state.chat_id, st.session_state.user)
        st.session_state.messages = []
        st.rerun()
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.user = None
        st.session_state.chat_id = None
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    st.session_state.persona = st.selectbox("Assistant Style", list(PERSONAS.keys()), format_func=lambda x: PERSONAS[x])
    st.divider()
    
    st.markdown("### 💬 Chat History")
    chats = get_chats(st.session_state.user)
    
    if not chats:
        st.caption("No conversations yet")
    
    for cid, title in chats:
        col1, col2 = st.columns([8, 2])
        with col1:
            if st.button(f"💬 {title[:30]}", key=f"chat_{cid}", use_container_width=True):
                st.session_state.chat_id = cid
                st.session_state.messages = load_messages(cid)
                st.rerun()
        with col2:
            if st.button("⋮", key=f"menu_{cid}"):
                st.session_state[f"menu_open_{cid}"] = not st.session_state.get(f"menu_open_{cid}", False)
        
        if st.session_state.get(f"menu_open_{cid}", False):
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✏️ Edit", key=f"edit_{cid}"):
                    st.session_state.show_edit_confirm = cid
                    st.session_state[f"menu_open_{cid}"] = False
            with col_b:
                if st.button("🗑️ Delete", key=f"del_{cid}"):
                    st.session_state.show_delete_confirm = cid
                    st.session_state[f"menu_open_{cid}"] = False
    
    # Delete confirmation
    if st.session_state.show_delete_confirm:
        st.warning(f"Delete this chat?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Yes", key="confirm_delete"):
                delete_chat(st.session_state.show_delete_confirm)
                if st.session_state.show_delete_confirm == st.session_state.chat_id:
                    new_id = str(uuid.uuid4())
                    st.session_state.chat_id = new_id
                    create_chat(new_id, st.session_state.user)
                    st.session_state.messages = []
                st.session_state.show_delete_confirm = None
                st.rerun()
        with col_no:
            if st.button("No", key="cancel_delete"):
                st.session_state.show_delete_confirm = None
                st.rerun()
    
    # Edit confirmation
    if st.session_state.show_edit_confirm:
        current_title = next((t for cid, t in chats if cid == st.session_state.show_edit_confirm), "")
        new_title = st.text_input("New chat name:", value=current_title, key="edit_input")
        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("Save", key="confirm_edit"):
                rename_chat(st.session_state.show_edit_confirm, new_title)
                st.session_state.show_edit_confirm = None
                st.rerun()
        with col_cancel:
            if st.button("Cancel", key="cancel_edit"):
                st.session_state.show_edit_confirm = None
                st.rerun()

# ---------------- MAIN AREA ----------------
st.title("Student AI Pro")
st.caption(f"Active: {PERSONAS[st.session_state.persona]}")

# =========================================================
# DISPLAY MESSAGES - WIDER HORIZONTALLY
# =========================================================
for msg in st.session_state.messages:
    if msg["role"] == "user":
        col1, col2, col3 = st.columns([1, 5, 6])
        with col3:
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; margin-bottom: 10px;">
                <div style="display: flex; align-items: flex-start; gap: 10px; flex-direction: row-reverse;">
                    <div style="background: #2563EB; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">👤</div>
                    <div style="background: linear-gradient(135deg, #2563EB, #1E40AF); color: white; padding: 10px 16px; border-radius: 18px 18px 5px 18px; max-width: 85%; min-width: 200px; word-wrap: break-word;">{msg['content']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        col1, col2, col3 = st.columns([6, 5, 1])
        with col1:
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-start; margin-bottom: 10px;">
                <div style="display: flex; align-items: flex-start; gap: 10px;">
                    <div style="background: #1E293B; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 1px solid #2563EB;">🤖</div>
                    <div style="background: #1E293B; color: #E2E8F0; padding: 10px 16px; border-radius: 18px 18px 18px 5px; max-width: 85%; min-width: 200px; word-wrap: break-word; border: 1px solid #334155;">{msg['content']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# =========================================================
# BOTTOM BAR WITH INPUT, FILE, VOICE
# =========================================================
st.markdown('<div class="bottom-bar">', unsafe_allow_html=True)

input_col, file_col, voice_col = st.columns([6, 1, 1])

with input_col:
    user_input = st.chat_input("Type your message...", key="main_input")

with file_col:
    uploaded = st.file_uploader(
        "📎",
        type=["pdf", "txt", "png", "jpg", "jpeg"],
        label_visibility="collapsed",
        key="file_uploader_bottom"
    )

with voice_col:
    if st.button("🎤", key="voice_btn_bottom", use_container_width=True):
        voice_text = listen()
        if voice_text:
            st.session_state.voice_input = voice_text
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# Process uploaded file
if uploaded and uploaded.name != st.session_state.file_name:
    with st.spinner("Processing..."):
        if "pdf" in uploaded.type:
            st.session_state.file_text = read_pdf(uploaded)
        elif "text" in uploaded.type:
            st.session_state.file_text = read_txt(uploaded)
        else:
            st.image(uploaded, width=100)
            st.session_state.file_text = read_image(uploaded)
    st.session_state.file_name = uploaded.name
    st.success(f"✅ Loaded: {st.session_state.file_name}")

# Show file status
if st.session_state.file_name:
    st.info(f"📎 Attached: {st.session_state.file_name}")

# Process voice input
if st.session_state.get("voice_input"):
    user_input = st.session_state.voice_input
    st.session_state.voice_input = None

if user_input:
    # Prepare message with file
    final_message = user_input
    if st.session_state.file_text:
        final_message = f"{user_input}\n\n📎 **{st.session_state.file_name}**\n{st.session_state.file_text[:1500]}"
        st.session_state.file_text = ""
        st.session_state.file_name = None
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": final_message})
    save_message(st.session_state.chat_id, "user", final_message)
    
    # Auto-generate chat title from first message
    chats = get_chats(st.session_state.user)
    current = next((c for c in chats if c[0] == st.session_state.chat_id), None)
    if current and current[1] == "New Chat":
        new_title = user_input[:35] + ("..." if len(user_input) > 35 else "")
        rename_chat(st.session_state.chat_id, new_title)
    
    # Memory detection
    if "my name is" in final_message.lower():
        match = re.search(r"my name is (\w+)", final_message.lower())
        if match:
            save_memory(st.session_state.user, "name", match.group(1).capitalize())
            st.toast(f"✨ I'll remember your name: {match.group(1).capitalize()}")
    
    # Build system prompt
    user_memory = load_memory(st.session_state.user)
    memory_text = "\n".join([f"- {k}: {v}" for k, v in user_memory.items()])
    
    system_prompt = f"""{PERSONAS[st.session_state.persona]}

User Info:
{memory_text if memory_text else "No stored information"}

Be helpful, conversational, and personalized."""

    # Prepare API messages
    api_messages = [{"role": "system", "content": system_prompt}]
    for msg in st.session_state.messages[-12:]:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Web search
    if needs_search(final_message):
        with st.spinner("🔍 Searching..."):
            web_results = search_web(final_message)
            if web_results:
                api_messages.append({"role": "system", "content": f"Web Results:\n{web_results}"})
    
    # Generate response
    try:
        with st.spinner("Thinking..."):
            response = client.chat.completions.create(
                model=MODEL,
                messages=api_messages,
                temperature=0.7,
                max_tokens=2000
            )
            ai_response = response.choices[0].message.content
        
        # Add AI response
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        save_message(st.session_state.chat_id, "assistant", ai_response)
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
    
    st.rerun()