import os
import time
import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="مساعد التوصيف الوظيفي - جامعة الأزهر", page_icon="🎓", layout="centered")
import base64
def _b64(p):
    try:
        return base64.b64encode(open(p, "rb").read()).decode()
    except Exception:
        return ""
_logo = _b64("logo.png")
_img = f'<img src="data:image/png;base64,{_logo}" style="height:92px">' if _logo else ""
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
html, body, .stApp, [class*="css"] {font-family:'Cairo',sans-serif !important; direction:rtl; text-align:right}
.stApp {background:linear-gradient(180deg,#f4f8f6 0%,#ffffff 60%)}
.hdr {background:linear-gradient(135deg,#0b3d2e,#1b6b4f); color:#fff; border-radius:18px; padding:22px 26px; display:flex; align-items:center; gap:20px; box-shadow:0 6px 18px rgba(11,61,46,.25); border-bottom:4px solid #c9a227; margin-bottom:18px}
.hdr img {background:#fff; border-radius:12px; padding:6px}
.hdr h1 {margin:0; font-size:1.55rem; color:#fff; font-weight:700}
.hdr p {margin:4px 0 0; color:#e6d9a8; font-size:.95rem}
[data-testid="stChatMessage"] {border-radius:14px; border:1px solid #e3ece7; background:#fff}
</style>
""", unsafe_allow_html=True)
st.markdown(f'<div class="hdr">{_img}<div><h1>مساعد التوصيف الوظيفي</h1><p>جامعة الأزهر</p><p style="font-size:.8rem">المرجع: كتيب التوصيف الوظيفي 2023 - 2026</p></div></div>', unsafe_allow_html=True)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = ""
if not api_key:
    st.error("لم يتم العثور على مفتاح GEMINI_API_KEY في الإعدادات.")
    st.stop()

with open("context.txt", "r", encoding="utf-8") as f:
    doc_context = f.read()

system_instruction = f"""
أنت مساعد ذكي مخصص للعاملين بجامعة الأزهر، ومرجعك الوحيد والمعتمد هو كتيب التوصيف الوظيفي (2023 - 2026) المرفق أدناه.

القواعد الصارمة:
1. أجب فقط من المعلومات الواردة صراحةً في النص المرجعي التالي.
2. يُمنع تماماً الاعتماد على معلومات خارجية أو تخمينات أو استنتاجات غير موجودة في النص.
3. إذا سأل المستخدم عن معلومة غير موجودة في النص أو خارج اختصاص الكتيب، اعتذر بلطف ووضوح وقل: "عذراً، هذه المعلومة غير متوفرة في كتيب التوصيف الوظيفي المعتمد لدي، وهذا خارج نطاق اختصاصي الحالي."
4. اذكر اسم القسم أو اللجنة أو المادة أو الإدارة المذكورة في النص عند الإجابة.

النص المرجعي:
{doc_context}
"""

client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30000))


@st.cache_data(ttl=3600)
def get_models():
    prefs = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.5-flash"]
    found = []
    try:
        for m in client.models.list():
            n = m.name.replace("models/", "")
            if "flash" in n and "gemini" in n and not any(x in n for x in ("image", "tts", "live", "audio", "preview", "exp", "thinking")):
                found.append(n)
    except Exception:
        pass
    return prefs

if "messages" not in st.session_state:
    st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("اكتب سؤالك بخصوص التوصيف الوظيفي...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    answer = ""
    last_err = ""
    with st.chat_message("assistant"):
        box = st.empty()
        box.markdown("⏳ جارٍ البحث في الكتيب...")
        combos = [(m, t) for m in get_models() for t in (True, False)]
        for model, think in combos:
            try:
                if think:
                    cfg = types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.1, thinking_config=types.ThinkingConfig(thinking_level="low"))
                else:
                    cfg = types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.1)
                for chunk in client.models.generate_content_stream(
                    model=model,
                    contents=prompt,
                    config=cfg,
                ):
                    if chunk.text:
                        answer += chunk.text
                        box.markdown(answer)
                if answer:
                    break
            except Exception as e:
                last_err = type(e).__name__ + ": " + str(e)[:200].replace(api_key, "***")
                if answer:
                    break
                time.sleep(1)
        if not answer:
            answer = "عذراً، الخدمة مشغولة حالياً. حاول مرة أخرى بعد قليل.\n\n`" + last_err + "`"
            box.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
