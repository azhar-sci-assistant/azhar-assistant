import os
import time
import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="مساعد التوصيف الوظيفي - علوم الأزهر", page_icon="🎓")
st.markdown("<style>body,.stApp{direction:rtl;text-align:right}</style>", unsafe_allow_html=True)
st.title("مساعد التوصيف الوظيفي لأعضاء هيئة التدريس")
st.caption("كلية العلوم – فرع البنات بالقاهرة (جامعة الأزهر) | المرجع: كتيب 2023 - 2026")

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
أنت مساعد ذكي مخصص لأعضاء هيئة التدريس بكلية العلوم – فرع البنات بالقاهرة (جامعة الأزهر)، ومرجعك الوحيد والمعتمد هو كتيب التوصيف الوظيفي (2023 - 2026) المرفق أدناه.

القواعد الصارمة:
1. أجب فقط من المعلومات الواردة صراحةً في النص المرجعي التالي.
2. يُمنع تماماً الاعتماد على معلومات خارجية أو تخمينات أو استنتاجات غير موجودة في النص.
3. إذا سأل المستخدم عن معلومة غير موجودة في النص أو خارج اختصاص الكتيب، اعتذر بلطف ووضوح وقل: "عذراً، هذه المعلومة غير متوفرة في كتيب التوصيف الوظيفي المعتمد لدي، وهذا خارج نطاق اختصاصي الحالي."
4. اذكر اسم القسم أو اللجنة أو المادة أو الإدارة المذكورة في النص عند الإجابة.

النص المرجعي:
{doc_context}
"""

client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=40000))


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
    answer = None
    last_err = ""
    used = ""
    for model in get_models()[:3]:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.1),
                )
                answer = response.text
                used = model
                break
            except Exception as e:
                last_err = type(e).__name__ + ": " + str(e)[:200].replace(api_key, "***")
                time.sleep(2)
        if answer:
            break
    if not answer:
        answer = "عذراً، الخدمة مشغولة حالياً. حاول مرة أخرى بعد قليل.\n\n`" + last_err + "`"
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state["used"] = used
    with st.chat_message("assistant"):
        st.markdown(answer)
