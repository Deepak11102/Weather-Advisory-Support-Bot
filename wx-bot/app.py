import uuid
import streamlit as st
from bot import graph as G, sops as S
from bot.llm import get_llm

st.set_page_config(page_title="SkyGuard · Weather Advisory", page_icon="⛅", layout="centered", initial_sidebar_state="expanded")

@st.cache_resource
def boot(): return G.build(), S.load(), get_llm()
graph, cat, llm = boot()

SEV = {s["id"]: s["severity"] for s in cat["sops"]}
COL = {"critical": "#e11d48", "high": "#f97316", "moderate": "#d99a00", "low": "#22c55e", "info": "#3b82f6"}
PROMPTS = [("🚲", "Is it safe to bike to work in Bhopal today?"), ("👶", "Should I take my kid to the park in Mumbai today?"),
           ("🧺", "Is it a good day for a picnic in Noida today?"), ("🏃", "Can I go for a run in Shimla tomorrow?")]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
.stApp { background: linear-gradient(160deg, #e0f2fe 0%, #f5f3ff 50%, #fef3c7 100%); }
#MainMenu, footer, .stDeployButton, [data-testid="stToolbar"] { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"], [data-testid="stSidebarCollapseButton"] { visibility: visible !important; }
[data-testid="stSidebar"] { background: rgba(255,255,255,.85); backdrop-filter: blur(8px); }
.hero { padding: 28px 30px; border-radius: 24px; color: #fff; margin-bottom: 18px;
  background: linear-gradient(120deg, #0ea5e9, #6366f1 60%, #a855f7); box-shadow: 0 12px 30px rgba(99,102,241,.35); }
.hero h1 { margin: 0; font-size: 2.1rem; font-weight: 700; }
.hero p { margin: 6px 0 0; opacity: .92; font-size: .98rem; }
.pill { display: inline-block; margin-top: 12px; padding: 4px 12px; border-radius: 999px; background: rgba(255,255,255,.22); font-size: .8rem; }
div[data-testid="stChatMessage"] { background: rgba(255,255,255,.75); border-radius: 18px; padding: 14px 18px;
  box-shadow: 0 4px 14px rgba(0,0,0,.06); backdrop-filter: blur(6px); }
.stButton > button { border-radius: 14px; border: 1px solid #c7d2fe; background: #fff; color: #3730a3; font-weight: 600;
  padding: 10px 14px; transition: all .15s; width: 100%; }
.stButton > button:hover { transform: translateY(-2px); border-color: #6366f1; box-shadow: 0 6px 16px rgba(99,102,241,.25); }
.badge { display: inline-block; color: #fff; padding: 3px 11px; border-radius: 999px; font-size: .75rem; font-weight: 600; margin: 4px 6px 4px 0; }
.grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0 4px; }
.card { background: #fff; border-radius: 14px; padding: 10px 6px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.card .v { font-weight: 700; font-size: 1.05rem; color: #1e1b4b; } .card .k { font-size: .7rem; color: #64748b; }
@media (max-width: 600px) { .grid { grid-template-columns: repeat(2, 1fr); } }
</style>
""", unsafe_allow_html=True)

st.session_state.setdefault("tid", str(uuid.uuid4()))
st.session_state.setdefault("msgs", [])

with st.sidebar:
    st.markdown("### ⛅ SkyGuard")
    st.caption("Answers come only from written safety policies (SOPs) and live Open-Meteo data.")
    st.markdown("**How it works**\n1. 🧠 AI reads your question\n2. 🌍 Live weather is fetched\n3. 📋 Policies are checked by code\n4. 💬 You get a cited answer")
    st.metric("Policies loaded", len(cat["sops"]))
    st.caption("Mode: " + ("🟢 LLM (Groq)" if llm else "🟡 keyword fallback"))
    with st.expander("View all policies"):
        for s in cat["sops"]: st.markdown(f"`{s['id']}` {s['title']}")
    if st.button("🗑️ New chat"):
        st.session_state.tid, st.session_state.msgs = str(uuid.uuid4()), []
        st.rerun()

st.markdown(f"""<div class="hero"><h1>⛅ SkyGuard</h1>
<p>Ask if the weather is safe for your plan. Every answer is backed by a policy and real numbers.</p>
<span class="pill">{len(cat['sops'])} safety policies · live forecast</span></div>""", unsafe_allow_html=True)

def stats(r):
    f, u = r.get("facts") or {}, r.get("units") or {}
    spec = [("🌡️", "Temperature", "temperature_2m.current"), ("💨", "Max wind", "wind_speed_10m.window_max"),
            ("🌧️", "Rain chance", "precipitation_probability.window_max"), ("☀️", "UV max", "uv_index.window_max")]
    return [(i, n, f"{f[k]:g} {u.get(k.split('.')[0], '')}".strip()) for i, n, k in spec if k in f]

def render(m):
    with st.chat_message(m["role"], avatar="🧑" if m["role"] == "user" else "⛅"):
        st.markdown(m["text"])
        if m.get("badges"):
            st.markdown("".join(f'<span class="badge" style="background:{COL[SEV[i]]}">{i} · {SEV[i]}</span>' for i in m["badges"]), unsafe_allow_html=True)
        if m.get("stats"):
            st.markdown('<div class="grid">' + "".join(f'<div class="card"><div>{i}</div><div class="v">{v}</div><div class="k">{n}</div></div>' for i, n, v in m["stats"]) + "</div>", unsafe_allow_html=True)
        if m.get("why"):
            with st.expander("🔍 Why this answer?"): st.json(m["why"])

if not st.session_state.msgs:
    st.markdown("##### 💡 Try asking")
    cols = st.columns(2)
    for n, (icon, p) in enumerate(PROMPTS):
        if cols[n % 2].button(f"{icon} {p}", key=f"p{n}"):
            st.session_state.pending = p
            st.rerun()

for m in st.session_state.msgs: render(m)

q = st.chat_input("Ask about cycling, running, hiking, travel, kids, pets, picnics...") or st.session_state.pop("pending", None)
if q:
    st.session_state.msgs.append({"role": "user", "text": q})
    with st.spinner("⛅ Checking live weather and policies..."):
        try:
            r = G.ask(graph, q, st.session_state.tid, sops=cat, llm=llm)
            log = r.get("log") or []
            last = max((i for i, l in enumerate(log) if l.startswith("understand:")), default=0)
            why = {"matched_sops": r.get("matched"), "mode": r.get("mode"), "used_template_fallback": r.get("used_fallback"),
                   "facts_used": G.shown(r, cat) if r.get("matched") else {}, "trace": log[last:]}
            out = {"role": "assistant", "text": r["reply"], "why": why, "badges": r.get("matched") or [], "stats": stats(r)}
        except Exception as e:
            out = {"role": "assistant", "text": f"Something went wrong internally ({type(e).__name__}); I won't guess an answer."}
    st.session_state.msgs.append(out)
    st.rerun()