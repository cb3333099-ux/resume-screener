import re
import json
import datetime
from urllib.parse import quote_plus
import streamlit as st
import pypdf
from io import BytesIO
import plotly.graph_objects as go

st.set_page_config(
    page_title="Resume Screener AI",
    layout="wide",
    page_icon="📄",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* ── Dark theme base ──────────────────────────────────────── */
    html, body, [data-testid="stApp"] {
        background-color: #0E1117 !important;
        color: #E5E7EB !important;
    }
    [data-testid="stSidebar"] {
        background-color: #1C2128 !important;
        border-right: 1px solid #30363D;
    }
    [data-testid="stSidebar"] * { color: #E5E7EB !important; }

    /* ── Header branding ──────────────────────────────────────── */
    .app-header {
        display: flex; align-items: center; gap: 14px;
        padding: 18px 0 10px 0; margin-bottom: 6px;
    }
    .app-header .logo {
        font-size: 2.4rem; line-height: 1;
    }
    .app-header .title-block h1 {
        margin: 0; font-size: 1.9rem; font-weight: 800;
        background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .app-header .title-block p {
        margin: 0; font-size: 0.82rem; color: #9CA3AF;
    }

    /* ── Metric cards ─────────────────────────────────────────── */
    .metric-card {
        background: #1C2128;
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 20px 18px;
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    }
    .metric-card:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 6px 20px rgba(59,130,246,0.25);
    }
    .metric-card .mc-icon  { font-size: 1.6rem; margin-bottom: 6px; }
    .metric-card .mc-label { font-size: 0.75rem; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px; }
    .metric-card .mc-value { font-size: 2rem; font-weight: 800; color: #E5E7EB; line-height: 1.1; }
    .metric-card .mc-badge { display:inline-block; margin-top:8px; padding:3px 12px; border-radius:20px; font-size:0.75rem; font-weight:700; }
    .mc-badge-green  { background:rgba(16,185,129,0.2); color:#10B981; border:1px solid rgba(16,185,129,0.4); }
    .mc-badge-yellow { background:rgba(251,191,36,0.2);  color:#FBBF24; border:1px solid rgba(251,191,36,0.4); }
    .mc-badge-red    { background:rgba(239,68,68,0.2);   color:#EF4444; border:1px solid rgba(239,68,68,0.4); }

    /* ── Skill badges ─────────────────────────────────────────── */
    .badge { display:inline-block; padding:4px 14px; border-radius:20px; font-weight:700; font-size:0.88rem; letter-spacing:0.03em; }
    .badge-green  { background:rgba(16,185,129,0.2);  color:#10B981; border:1px solid rgba(16,185,129,0.4); }
    .badge-yellow { background:rgba(251,191,36,0.2);  color:#FBBF24; border:1px solid rgba(251,191,36,0.4); }
    .badge-red    { background:rgba(239,68,68,0.2);   color:#EF4444; border:1px solid rgba(239,68,68,0.4); }

    /* ── Status colours ───────────────────────────────────────── */
    .status-ok   { color: #10B981; font-weight: 700; }
    .status-warn { color: #FBBF24; font-weight: 700; }
    .status-bad  { color: #EF4444; font-weight: 700; }
    .conf-high   { color: #10B981; font-weight: 700; }
    .conf-medium { color: #FBBF24; font-weight: 700; }
    .conf-low    { color: #EF4444; font-weight: 700; }

    /* ── Advanced matching cards ──────────────────────────────── */
    .adv-card {
        background: #1C2128; border-radius: 10px;
        padding: 14px 18px; margin-bottom: 8px;
        border-left: 4px solid #30363D;
        box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    }
    .adv-card strong { color: #E5E7EB; }
    .adv-card em     { color: #9CA3AF; }
    .adv-card.green  { border-left-color: #10B981; }
    .adv-card.yellow { border-left-color: #FBBF24; }
    .adv-card.red    { border-left-color: #EF4444; }
    .adv-card.blue   { border-left-color: #3B82F6; }

    /* ── Recommendation cards ─────────────────────────────────── */
    .rec-card {
        background: #1C2128; border-radius: 10px;
        padding: 14px 18px; margin-bottom: 10px;
        border-left: 5px solid #30363D;
        box-shadow: 0 1px 4px rgba(0,0,0,0.3);
        transition: box-shadow 0.2s ease;
    }
    .rec-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.5); }
    .rec-card strong { color: #E5E7EB; }
    .rec-high   { border-left-color: #EF4444; }
    .rec-medium { border-left-color: #FBBF24; }
    .rec-low    { border-left-color: #10B981; }
    .rec-card span { color: #9CA3AF !important; }

    /* ── Skill chips ──────────────────────────────────────────── */
    .skill-chip {
        display: inline-block; padding: 4px 12px;
        border-radius: 16px; font-size: 0.82rem;
        font-weight: 600; margin: 3px 3px;
        transition: transform 0.15s ease;
    }
    .skill-chip:hover { transform: scale(1.06); }
    .chip-high   { background:rgba(16,185,129,0.15); color:#10B981; border:1px solid rgba(16,185,129,0.35); }
    .chip-medium { background:rgba(251,191,36,0.15);  color:#FBBF24; border:1px solid rgba(251,191,36,0.35); }
    .chip-low    { background:rgba(239,68,68,0.15);   color:#EF4444; border:1px solid rgba(239,68,68,0.35); }

    /* ── Skill section badges (matched/missing/optional) ──────── */
    .skill-badge-green  { display:inline-block; padding:5px 14px; border-radius:16px; margin:3px; font-size:0.83rem; font-weight:600; background:rgba(16,185,129,0.15); color:#10B981; border:1px solid rgba(16,185,129,0.35); }
    .skill-badge-red    { display:inline-block; padding:5px 14px; border-radius:16px; margin:3px; font-size:0.83rem; font-weight:600; background:rgba(239,68,68,0.15);   color:#EF4444; border:1px solid rgba(239,68,68,0.35); }
    .skill-badge-yellow { display:inline-block; padding:5px 14px; border-radius:16px; margin:3px; font-size:0.83rem; font-weight:600; background:rgba(251,191,36,0.15);  color:#FBBF24; border:1px solid rgba(251,191,36,0.35); }

    /* ── ATS checklist ────────────────────────────────────────── */
    .ats-check { padding: 6px 0; }
    .ats-pass  { color: #10B981; }
    .ats-fail  { color: #EF4444; }

    /* ── Priority label pills ─────────────────────────────────── */
    .prio-high   { color:#EF4444; font-size:0.75rem; font-weight:700; }
    .prio-medium { color:#FBBF24; font-size:0.75rem; font-weight:700; }
    .prio-low    { color:#10B981; font-size:0.75rem; font-weight:700; }

    /* ── Streamlit native overrides ───────────────────────────── */
    div[data-testid="stMetricValue"] { color: #E5E7EB !important; }
    div[data-testid="stMetricLabel"] { color: #9CA3AF !important; }
    .stProgress > div > div { background: linear-gradient(90deg, #3B82F6, #8B5CF6) !important; border-radius: 4px; }
    div[data-testid="stTabs"] [role="tab"]          { color: #9CA3AF; font-weight: 600; }
    div[data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: #3B82F6 !important; border-bottom-color: #3B82F6 !important; }
    div.stButton > button {
        border-radius: 8px; font-weight: 600;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(59,130,246,0.35); }
    textarea, input[type="text"] {
        background-color: #1C2128 !important;
        color: #E5E7EB !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
    }
    textarea:focus, input[type="text"]:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 2px rgba(59,130,246,0.25) !important;
    }
    [data-testid="stFileUploader"] {
        background: #1C2128;
        border: 2px dashed #3B82F6;
        border-radius: 10px;
        transition: border-color 0.2s ease;
    }
    [data-testid="stFileUploader"]:hover { border-color: #8B5CF6; }

    /* ── Divider ──────────────────────────────────────────────── */
    hr { border-color: #30363D !important; }
    .dark-divider { border: none; border-top: 1px solid #30363D; margin: 16px 0; }

    /* ── History row ──────────────────────────────────────────── */
    .hist-row {
        background: #1C2128; border-radius: 10px;
        padding: 12px 16px; margin-bottom: 8px;
        border: 1px solid #30363D;
    }
    .hist-row:hover { border-color: #3B82F6; }

    /* ── Section header ───────────────────────────────────────── */
    .section-header {
        font-size: 1.05rem; font-weight: 700; color: #E5E7EB;
        border-bottom: 2px solid #3B82F6; padding-bottom: 6px;
        margin-bottom: 14px; display: inline-block;
    }

    /* ── Fade-in animation ────────────────────────────────────── */
    @keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
    .fade-in { animation: fadeIn 0.4s ease forwards; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── App header ─────────────────────────────────────────────────────
st.markdown(
    """
    <div class="app-header fade-in">
        <div class="logo">📄</div>
        <div class="title-block">
            <h1>Resume Screener AI</h1>
            <p>Powered by Hugging Face sentence-transformers &mdash; semantic AI/ML matching</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

SKILLS_DB = [
    "python","javascript","typescript","java","c++","c#","go","rust",
    "kotlin","swift","ruby","php","scala","r","matlab","bash","shell",
    "react","angular","vue","next.js","html","css","sass","tailwind",
    "bootstrap","webpack","vite",
    "node.js","django","flask","fastapi","spring","express","graphql","rest","grpc",
    "sql","postgresql","mysql","mongodb","redis","elasticsearch",
    "cassandra","dynamodb","sqlite",
    "aws","azure","gcp","docker","kubernetes","terraform","ansible",
    "jenkins","github actions","ci/cd","linux","nginx",
    "machine learning","deep learning","nlp","tensorflow","pytorch",
    "scikit-learn","pandas","numpy","spark","hadoop","tableau","power bi",
    "agile","scrum","microservices","git","jira","confluence",
]

EDUCATION_LEVELS = {
    "ph.d":5,"phd":5,"doctorate":5,"doctoral":5,
    "master":4,"m.s.":4,"m.sc":4,"mba":4,"m.eng":4,
    "bachelor":3,"b.s.":3,"b.sc":3,"b.eng":3,"b.tech":3,"undergraduate":3,
    "associate":2,
    "high school":1,"diploma":1,"ged":1,
}

SEMANTIC_WEIGHT   = 0.6
SKILL_WEIGHT      = 0.4
STRONG_MATCH_THRESHOLD   = 0.7
MODERATE_MATCH_THRESHOLD = 0.45

INDUSTRY_TRENDING_SKILLS = {
    "Cloud & DevOps": ["aws","azure","gcp","kubernetes","docker","terraform","ci/cd","github actions"],
    "AI & Data":      ["machine learning","deep learning","python","tensorflow","pytorch","pandas","numpy","nlp"],
    "Backend":        ["node.js","python","django","fastapi","postgresql","redis","microservices","rest"],
    "Frontend":       ["react","typescript","next.js","vue","angular","tailwind","webpack"],
    "Practices":      ["agile","git","scrum","linux","elasticsearch","mongodb"],
}

def init_session_state():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "saved_analyses" not in st.session_state:
        st.session_state.saved_analyses = {}
    if "bookmarks" not in st.session_state:
        st.session_state.bookmarks = []

init_session_state()

def get_color_badge(score):
    pct = score * 100
    if pct >= 80: return "badge-green","Excellent Fit","\U0001f7e2"
    if pct >= 60: return "badge-yellow","Good Fit","\U0001f7e1"
    return "badge-red","Poor Fit","\U0001f534"

def render_badge(score):
    css,label,_ = get_color_badge(score)
    return f'<span class="badge {css}">{label} \u2014 {score*100:.1f}%</span>'

def stars(score):
    filled = round(score*5)
    return "\u2605"*filled + "\u2606"*(5-filled)

def extract_skills(text):
    tl = text.lower()
    return [s for s in SKILLS_DB if s in tl]

@st.cache_resource(show_spinner=False)
def load_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")

def semantic_similarity(model, text_a, text_b):
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    emb = model.encode([text_a, text_b])
    score = cosine_similarity([emb[0]], [emb[1]])[0][0]
    return float(np.clip(score, 0.0, 1.0))

def extract_years_experience(text):
    patterns = [
        r'(\d+)\+?\s*(?:years?|yrs?)[\s\-]+(?:of[\s\-]+)?(?:experience|exp\b)',
        r'(?:experience|exp\b)[\s\-]+(?:of[\s\-]+)?(\d+)\+?\s*(?:years?|yrs?)',
        r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:in|with|using)\b',
        r'minimum\s+(?:of\s+)?(\d+)\+?\s*(?:years?|yrs?)',
        r'at\s+least\s+(\d+)\+?\s*(?:years?|yrs?)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m: return float(m.group(1))
    return None

def extract_education_level(text):
    tl = text.lower()
    best_name,best_rank = "Not specified",0
    for term,rank in EDUCATION_LEVELS.items():
        if term in tl and rank > best_rank:
            best_name,best_rank = term.title(),rank
    return best_name,best_rank

def extract_salary_range(text):
    patterns = [
        r'\$\s*(\d+(?:\.\d+)?)\s*[Kk]\s*[-\u2013\u2014to]+\s*\$?\s*(\d+(?:\.\d+)?)\s*[Kk]',
        r'\$\s*(\d{3,6}(?:,\d{3})?)\s*[-\u2013\u2014to]+\s*\$?\s*(\d{3,6}(?:,\d{3})?)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            low  = float(m.group(1).replace(',',''))
            high = float(m.group(2).replace(',',''))
            if low  > 1000: low  /= 1000
            if high > 1000: high /= 1000
            return low,high
    return None

def extract_location(text):
    tl = text.lower()
    has_remote = "remote" in tl
    has_hybrid = "hybrid" in tl
    has_onsite = any(kw in tl for kw in ("on-site","onsite","in-office","in office"))
    if has_remote and has_hybrid: return "Hybrid / Remote"
    if has_remote: return "Remote"
    if has_hybrid: return "Hybrid"
    if has_onsite: return "On-site"
    m = re.search(r'(?:location|based in|office in)\s*[:\-]?\s*([A-Z][a-zA-Z\s]+(?:,\s*[A-Z]{2})?)', text, re.IGNORECASE)
    if m: return m.group(1).strip()
    return "Not specified"

def calculate_experience_match(resume_years, required_years):
    if resume_years is None or required_years is None: return "Unknown","status-warn"
    if resume_years >= required_years * 1.5: return "Overqualified","status-warn"
    if resume_years >= required_years: return "Qualified \u2714","status-ok"
    return "Underqualified","status-bad"

def calculate_ats_score_detailed(resume_text, job_description):
    checks,warnings = [],[]
    tl = resume_text.lower()

    has_email = bool(re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', resume_text))
    checks.append(("Email address", has_email, "Found" if has_email else "No email detected"))
    if not has_email: warnings.append("Add your email address \u2014 ATS systems require contact info.")

    has_phone = bool(re.search(r'[\+\(]?\d[\d\s\(\)\-\.]{7,}\d', resume_text))
    checks.append(("Phone number", has_phone, "Found" if has_phone else "No phone number detected"))
    if not has_phone: warnings.append("Add a phone number for recruiters to reach you.")

    important_headers = ["experience","education","skills"]
    found_headers = [h for h in important_headers if h in tl]
    has_headers = len(found_headers) >= 2
    checks.append(("Section headers", has_headers,
        f"Found: {', '.join(found_headers)}" if found_headers else "Missing standard section headers"))
    missing_hdrs = [h.upper() for h in important_headers if h not in found_headers]
    if missing_hdrs: warnings.append(f"Add clear section headers: {', '.join(missing_hdrs)}.")

    bad_chars = sum(resume_text.count(c) for c in ["\u2502","\u250c","\u2514","\u2510","\u2518","\u2500","\u2550","\u2551"])
    has_clean = bad_chars < 5
    checks.append(("Clean formatting", has_clean,
        "No problematic characters" if has_clean else f"Found {bad_chars} characters that may confuse ATS parsers"))
    if not has_clean: warnings.append("Remove special box-drawing characters that break ATS parsers.")

    job_kw    = set(extract_skills(job_description))
    resume_kw = set(extract_skills(resume_text))
    density   = len(resume_kw & job_kw) / len(job_kw) if job_kw else 1.0
    has_kw    = density >= 0.5
    checks.append(("Keyword density", has_kw, f"{density*100:.0f}% of required keywords found"))
    if not has_kw:
        missing_kw = sorted(job_kw - resume_kw)[:5]
        warnings.append(f"Low keyword match. Add skills like: {', '.join(missing_kw)}.")

    word_count  = len(resume_text.split())
    good_length = 200 <= word_count <= 2000
    checks.append(("Resume length", good_length,
        f"{word_count} words ({'good' if good_length else 'too short or too long'})"))
    if not good_length:
        warnings.append("Resume is too short \u2014 add more detail." if word_count < 200
                        else "Resume may be too long \u2014 consider condensing to 1\u20132 pages.")

    has_summary = any(kw in tl for kw in ("summary","objective","profile","about"))
    checks.append(("Professional summary", has_summary, "Found" if has_summary else "No summary section detected"))
    if not has_summary:
        warnings.append("Add a professional summary at the top for ATS and recruiters.")

    weights = [0.15, 0.10, 0.20, 0.15, 0.25, 0.10, 0.05]
    score   = sum(w for (_,passed,_),w in zip(checks, weights) if passed)
    return {"score": score, "checks": checks, "warnings": warnings}

def generate_recommendations(missing_skills, matched_skills, bonus_skills,
                              ats_warnings, exp_status, edu_status,
                              semantic_score, combined_score):
    recs = []
    for skill in sorted(missing_skills)[:3]:
        recs.append({"priority":"high","icon":"\U0001f534",
            "title":f"Add '{skill.title()}' experience",
            "detail":(f"'{skill.title()}' is required but missing from your resume. "
                      "Consider an online course or a project using this skill.")})
    for warning in ats_warnings[:2]:
        recs.append({"priority":"high","icon":"\u26a0\ufe0f","title":"ATS Compatibility Issue","detail":warning})
    if exp_status == "Underqualified":
        recs.append({"priority":"high","icon":"\U0001f4bc",
            "title":"Increase highlighted experience",
            "detail":"Quantify achievements and include all relevant roles, including freelance and side projects."})
    elif exp_status == "Overqualified":
        recs.append({"priority":"medium","icon":"\U0001f4bc",
            "title":"Tailor your resume to the role level",
            "detail":"Emphasise passion for the role and alignment with team goals rather than seniority."})
    if "Does not meet" in edu_status:
        recs.append({"priority":"medium","icon":"\U0001f393",
            "title":"Address education gap",
            "detail":"Highlight certifications, bootcamps, or equivalent practical experience."})
    if semantic_score >= 0.6 and len(missing_skills) > len(matched_skills):
        recs.append({"priority":"medium","icon":"\U0001f9e0",
            "title":"Add more explicit skill keywords",
            "detail":"Add a dedicated Skills section listing all technologies you know."})
    trending_all = [s for cat in INDUSTRY_TRENDING_SKILLS.values() for s in cat]
    for skill in [s for s in bonus_skills if s in trending_all][:2]:
        recs.append({"priority":"low","icon":"\U0001f31f",
            "title":f"Highlight your '{skill.title()}' skill",
            "detail":f"'{skill.title()}' is a valuable trending skill. Make it prominent to stand out."})
    if combined_score >= 0.8 and len(recs) < 2:
        recs.append({"priority":"low","icon":"\u2705",
            "title":"Strong match \u2014 fine-tune for perfection",
            "detail":"Quantify more achievements (e.g. 'reduced load time by 40%') to stand out further."})
    seen,unique_recs = set(),[]
    for r in recs:
        if r["title"] not in seen:
            seen.add(r["title"])
            unique_recs.append(r)
    priority_order = {"high":0,"medium":1,"low":2}
    unique_recs.sort(key=lambda r: priority_order[r["priority"]])
    return unique_recs[:5]

def get_skill_confidence(skill, resume_text):
    tl    = resume_text.lower()
    count = tl.count(skill.lower())
    m = re.search(
        r'(?:skills?|technologies|tech stack|competencies)[^\n]{0,30}\n(.{0,500})',
        resume_text, re.IGNORECASE | re.DOTALL)
    in_section = m and skill.lower() in m.group(1).lower()
    if in_section or count >= 3: return 90,"high"
    if count == 2: return 70,"medium"
    if count == 1: return 45,"low"
    return 20,"low"

def get_industry_trends(missing_skills, job_description):
    RESOURCES = {
        "aws":"https://aws.amazon.com/training/",
        "azure":"https://learn.microsoft.com/en-us/training/",
        "gcp":"https://cloud.google.com/learn/training",
        "kubernetes":"https://kubernetes.io/docs/tutorials/",
        "docker":"https://docs.docker.com/get-started/",
        "terraform":"https://developer.hashicorp.com/terraform/tutorials",
        "ci/cd":"https://www.atlassian.com/continuous-delivery",
        "machine learning":"https://www.coursera.org/learn/machine-learning",
        "deep learning":"https://www.deeplearning.ai/",
        "python":"https://docs.python.org/3/tutorial/",
        "tensorflow":"https://www.tensorflow.org/learn",
        "pytorch":"https://pytorch.org/tutorials/",
        "react":"https://react.dev/learn",
        "typescript":"https://www.typescriptlang.org/docs/",
        "node.js":"https://nodejs.org/en/learn/",
        "postgresql":"https://www.postgresql.org/docs/",
        "redis":"https://redis.io/learn",
        "microservices":"https://microservices.io/",
        "git":"https://git-scm.com/doc",
        "agile":"https://www.agilealliance.org/agile101/",
    }
    seen,results = set(),[]
    for category,skills in INDUSTRY_TRENDING_SKILLS.items():
        for skill in skills:
            if skill in missing_skills and skill not in seen:
                seen.add(skill)
                results.append({"skill":skill,"category":category,
                    "resource":RESOURCES.get(skill,
                        "https://www.google.com/search?q=" + quote_plus("learn " + skill))})
            if len(results) == 5: return results
    return results

_DARK_BG   = "#0E1117"
_DARK_CARD = "#1C2128"
_DARK_GRID = "#30363D"
_DARK_TEXT = "#E5E7EB"

def _dark_layout(**kwargs):
    base = dict(
        paper_bgcolor=_DARK_CARD,
        plot_bgcolor=_DARK_CARD,
        font=dict(color=_DARK_TEXT),
        margin=dict(t=50,b=20,l=20,r=60),
    )
    base.update(kwargs)
    return base

def create_skill_chart(matched, missing, bonus):
    fig = go.Figure(go.Pie(
        labels=["Matched","Missing","Bonus"],
        values=[matched, missing, bonus],
        hole=0.45,
        marker=dict(colors=["#10B981","#EF4444","#8B5CF6"],line=dict(color=_DARK_CARD,width=3)),
        textinfo="label+percent",
        textfont=dict(color=_DARK_TEXT),
        hovertemplate="%{label}: %{value} skill(s)<extra></extra>",
    ))
    fig.update_layout(title=dict(text="Skill Breakdown",font=dict(size=16,color=_DARK_TEXT)),
                      showlegend=True, height=340,
                      **_dark_layout(margin=dict(t=50,b=10,l=10,r=10)))
    return fig

def create_score_chart(semantic, skill, combined):
    scores     = [semantic*100, skill*100, combined*100]
    categories = ["Semantic Similarity","Skill Match","Overall Score"]
    colors     = ["#10B981" if s>=80 else "#FBBF24" if s>=60 else "#EF4444" for s in scores]
    fig = go.Figure(go.Bar(x=scores,y=categories,orientation="h",
        marker_color=colors, text=[f"{s:.1f}%" for s in scores],
        textposition="outside", textfont=dict(color=_DARK_TEXT),
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>"))
    fig.update_layout(title=dict(text="Score Breakdown",font=dict(size=16,color=_DARK_TEXT)),
        xaxis=dict(range=[0,115],ticksuffix="%",showgrid=True,gridcolor=_DARK_GRID,color=_DARK_TEXT),
        yaxis=dict(autorange="reversed",color=_DARK_TEXT), height=240,
        **_dark_layout())
    return fig

def create_confidence_chart(skill_confidences):
    if not skill_confidences: return go.Figure()
    skills = list(skill_confidences.keys())
    confs  = [skill_confidences[s][0] for s in skills]
    level_colors = {"high":"#10B981","medium":"#FBBF24","low":"#EF4444"}
    bar_colors   = [level_colors[skill_confidences[s][1]] for s in skills]
    fig = go.Figure(go.Bar(x=confs,y=skills,orientation="h",
        marker_color=bar_colors, text=[f"{c}%" for c in confs],
        textposition="outside", textfont=dict(color=_DARK_TEXT),
        hovertemplate="%{y}: %{x}% confidence<extra></extra>"))
    fig.update_layout(title=dict(text="Skill Match Confidence",font=dict(size=16,color=_DARK_TEXT)),
        xaxis=dict(range=[0,120],ticksuffix="%",showgrid=True,gridcolor=_DARK_GRID,color=_DARK_TEXT),
        yaxis=dict(autorange="reversed",color=_DARK_TEXT),
        height=max(200, 30*len(skills)+60),
        **_dark_layout())
    return fig

def export_to_pdf(resume_name, job_title, combined_score, semantic_score,
                  skill_score, ats_score, matched_skills, missing_skills,
                  recommendations, ats_checks, ats_warnings, skill_confidences,
                  analysis_date=None):
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()

    GREEN  = rl_colors.HexColor("#28a745")
    YELLOW = rl_colors.HexColor("#ffc107")
    RED    = rl_colors.HexColor("#dc3545")
    DARK   = rl_colors.HexColor("#212529")
    LIGHT  = rl_colors.HexColor("#f8f9fa")

    def sc(pct):
        return GREEN if pct >= 80 else YELLOW if pct >= 60 else RED

    title_style  = ParagraphStyle("t",  parent=styles["Title"],   fontSize=20, spaceAfter=4,  textColor=DARK)
    sub_style    = ParagraphStyle("s",  parent=styles["Normal"],  fontSize=10, spaceAfter=12, textColor=rl_colors.grey)
    h2_style     = ParagraphStyle("h2", parent=styles["Heading2"],fontSize=13, spaceBefore=12,spaceAfter=6, textColor=DARK)
    rec_t_style  = ParagraphStyle("rt", parent=styles["Normal"],  fontSize=10, fontName="Helvetica-Bold", spaceAfter=2)
    rec_d_style  = ParagraphStyle("rd", parent=styles["Normal"],  fontSize=9,  leftIndent=20, spaceAfter=8, textColor=rl_colors.HexColor("#555555"))
    footer_style = ParagraphStyle("f",  parent=styles["Normal"],  fontSize=8,  textColor=rl_colors.grey, alignment=TA_CENTER)

    story = []
    story.append(Paragraph("AI Resume Screener \u2014 Analysis Report", title_style))
    timestamp = analysis_date or datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(
        f"Resume: <b>{resume_name}</b>  |  "
        f"Job: <b>{job_title or 'N/A'}</b>  |  "
        f"Generated: <b>{timestamp}</b>",
        sub_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK))
    story.append(Spacer(1, 0.15*inch))

    # Score table
    story.append(Paragraph("Overall Match Scores", h2_style))
    sd = [
        ["Metric","Score","Status"],
        ["Overall Match",  f"{combined_score*100:.1f}%", "Excellent" if combined_score>=0.8 else "Good" if combined_score>=0.6 else "Poor"],
        ["Semantic Score", f"{semantic_score*100:.1f}%", "Excellent" if semantic_score>=0.8  else "Good" if semantic_score>=0.6  else "Poor"],
        ["Skill Match",    f"{skill_score*100:.1f}%",    "Excellent" if skill_score>=0.8     else "Good" if skill_score>=0.6     else "Poor"],
        ["ATS Readiness",  f"{ats_score*100:.1f}%",      "Excellent" if ats_score>=0.8       else "Good" if ats_score>=0.6       else "Poor"],
    ]
    st_tbl = Table(sd, colWidths=[2.5*inch, 1.5*inch, 2*inch])
    st_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),DARK),("TEXTCOLOR",(0,0),(-1,0),rl_colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[LIGHT,rl_colors.white]),("FONTSIZE",(0,0),(-1,-1),10),
        ("GRID",(0,0),(-1,-1),0.5,rl_colors.lightgrey),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    for ri, row in enumerate(sd[1:], start=1):
        pct = float(row[1].rstrip("%"))
        st_tbl.setStyle(TableStyle([("TEXTCOLOR",(2,ri),(2,ri),sc(pct))]))
    story.append(st_tbl)
    story.append(Spacer(1, 0.15*inch))

    # Skills table
    story.append(HRFlowable(width="100%",thickness=0.5,color=rl_colors.lightgrey))
    story.append(Paragraph("Skills Analysis", h2_style))
    ml = sorted(matched_skills)
    xl = sorted(missing_skills)
    mr = max(len(ml),len(xl),1)
    skills_data = [["Matched Skills","Missing Skills"]]
    for i in range(mr):
        skills_data.append([
            ml[i].title() if i < len(ml) else "",
            xl[i].title() if i < len(xl) else "",
        ])
    sk_tbl = Table(skills_data, colWidths=[3*inch, 3*inch])
    sk_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),DARK),("TEXTCOLOR",(0,0),(-1,0),rl_colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),
        ("ALIGN",(0,0),(-1,-1),"LEFT"),("ROWBACKGROUNDS",(0,1),(-1,-1),[LIGHT,rl_colors.white]),
        ("GRID",(0,0),(-1,-1),0.5,rl_colors.lightgrey),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("TEXTCOLOR",(0,1),(0,-1),GREEN),("TEXTCOLOR",(1,1),(1,-1),RED),
    ]))
    story.append(sk_tbl)
    story.append(Spacer(1, 0.15*inch))

    # Recommendations
    if recommendations:
        story.append(HRFlowable(width="100%",thickness=0.5,color=rl_colors.lightgrey))
        story.append(Paragraph("Top Recommendations", h2_style))
        for i,rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"{i}. {rec['title']} [{rec['priority'].upper()}]", rec_t_style))
            story.append(Paragraph(rec["detail"], rec_d_style))

    # ATS breakdown
    story.append(HRFlowable(width="100%",thickness=0.5,color=rl_colors.lightgrey))
    story.append(Paragraph("ATS Compatibility Report", h2_style))
    ad = [["Check","Status","Detail"]]
    for label,passed,detail in ats_checks:
        ad.append([label, "Pass" if passed else "Fail", detail])
    at_tbl = Table(ad, colWidths=[2*inch,0.8*inch,3.7*inch])
    at_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),DARK),("TEXTCOLOR",(0,0),(-1,0),rl_colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),
        ("ALIGN",(0,0),(-1,-1),"LEFT"),("ROWBACKGROUNDS",(0,1),(-1,-1),[LIGHT,rl_colors.white]),
        ("GRID",(0,0),(-1,-1),0.5,rl_colors.lightgrey),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),8),
    ]))
    for ri,(_,passed,_) in enumerate(ats_checks,start=1):
        at_tbl.setStyle(TableStyle([("TEXTCOLOR",(1,ri),(1,ri), GREEN if passed else RED)]))
    story.append(at_tbl)

    story.append(Spacer(1, 0.3*inch))
    story.append(HRFlowable(width="100%",thickness=0.5,color=rl_colors.lightgrey))
    story.append(Paragraph(
        "Generated by AI Resume Screener \u00b7 Powered by Hugging Face sentence-transformers",
        footer_style))
    doc.build(story)
    return buf.getvalue()

def save_to_history(record):
    st.session_state.history.insert(0, record)
    if len(st.session_state.history) > 50:
        st.session_state.history = st.session_state.history[:50]

def extract_job_title(jd):
    for line in jd.strip().splitlines():
        line = line.strip()
        if line and len(line) < 80: return line
    return "Unknown Job"

def extract_company(jd):
    m = re.search(r'(?:company|organization|employer|at|join)\s*[:\-]?\s*([A-Z][a-zA-Z0-9\s&,\.]+)', jd, re.IGNORECASE)
    return m.group(1).strip()[:40] if m else "Unknown"

# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-header">📂 Inputs</div>', unsafe_allow_html=True)
    resume_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    bookmark_options  = ["— none —"] + [b["title"] for b in st.session_state.bookmarks]
    selected_bookmark = st.selectbox("📌 Load bookmarked job", bookmark_options, key="bm_select")
    default_jd = ""
    if selected_bookmark != "— none —":
        for bm in st.session_state.bookmarks:
            if bm["title"] == selected_bookmark:
                default_jd = bm["description"]
                break
    job_description = st.text_area("Paste Job Description", value=default_jd, height=250, key="jd_input")
    with st.expander("🔖 Save as Bookmark"):
        bm_title = st.text_input("Bookmark title", placeholder="e.g. Senior Engineer @ Google")
        if st.button("💾 Save Bookmark") and bm_title and job_description:
            if bm_title in [b["title"] for b in st.session_state.bookmarks]:
                st.warning("A bookmark with this title already exists.")
            else:
                st.session_state.bookmarks.append({"title":bm_title,"description":job_description})
                st.success(f"Saved: {bm_title}")
                st.rerun()
    st.markdown("---")
    if st.button("🗑️ Clear All", key="clear_all_btn", help="Clear resume and job description"):
        st.session_state.history = []
        st.session_state.saved_analyses = {}
        st.rerun()
    st.caption("Model: `all-MiniLM-L6-v2` (Hugging Face, free, no API key)")

# Main analysis
if resume_file and job_description:
    pdf_reader  = pypdf.PdfReader(BytesIO(resume_file.read()))
    resume_text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
    if not resume_text.strip():
        st.error("Could not extract text from the PDF. Please upload a text-based PDF.")
        st.stop()

    with st.spinner("\U0001f9e0 Loading AI model (first run may take ~30 s)\u2026"):
        model = load_model()

    semantic_score = semantic_similarity(model, resume_text, job_description)
    resume_skills  = set(extract_skills(resume_text))
    job_skills     = set(extract_skills(job_description))
    matched_skills = resume_skills & job_skills
    missing_skills = job_skills - resume_skills
    bonus_skills   = resume_skills - job_skills
    skill_score    = len(matched_skills) / len(job_skills) if job_skills else 0.0
    combined_score = SEMANTIC_WEIGHT * semantic_score + SKILL_WEIGHT * skill_score

    ats_result = calculate_ats_score_detailed(resume_text, job_description)
    ats_score  = ats_result["score"]

    resume_years   = extract_years_experience(resume_text)
    required_years = extract_years_experience(job_description)
    exp_status,exp_css = calculate_experience_match(resume_years, required_years)

    resume_edu_name,resume_edu_rank     = extract_education_level(resume_text)
    required_edu_name,required_edu_rank = extract_education_level(job_description)
    if required_edu_rank == 0:
        edu_status,edu_css = "Not specified","status-warn"
    elif resume_edu_rank >= required_edu_rank:
        edu_status,edu_css = "Meets requirement \u2714","status-ok"
    else:
        edu_status,edu_css = "Does not meet requirement","status-bad"

    recommendations   = generate_recommendations(missing_skills, matched_skills, bonus_skills,
                            ats_result["warnings"], exp_status, edu_status, semantic_score, combined_score)
    skill_confidences = {s: get_skill_confidence(s, resume_text) for s in sorted(matched_skills)}
    industry_trends   = get_industry_trends(missing_skills, job_description)
    salary_range      = extract_salary_range(job_description)
    location          = extract_location(job_description)
    visa_needed       = any(kw in job_description.lower() for kw in
                            ("visa sponsorship","work permit","work authorization","authorized to work"))
    job_title         = extract_job_title(job_description)
    company           = extract_company(job_description)
    resume_name       = resume_file.name

    history_record = {
        "resume_name":    resume_name,
        "job_title":      job_title,
        "company":        company,
        "overall_score":  round(combined_score*100,1),
        "ats_score":      round(ats_score*100,1),
        "date":           datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "semantic_score": round(semantic_score*100,1),
        "skill_score":    round(skill_score*100,1),
        "matched_skills": sorted(matched_skills),
        "missing_skills": sorted(missing_skills),
    }
    if not any(r == history_record for r in st.session_state.history):
        save_to_history(history_record)

    st.success("✅ Analysis complete!")

    # ── Metric cards row ──────────────────────────────────────────
    def _mc(icon, label, value_pct, extra=""):
        badge_cls = "mc-badge-green" if value_pct>=80 else "mc-badge-yellow" if value_pct>=60 else "mc-badge-red"
        badge_lbl = "Excellent" if value_pct>=80 else "Good" if value_pct>=60 else "Poor"
        return (
            f'<div class="metric-card fade-in">'
            f'<div class="mc-icon">{icon}</div>'
            f'<div class="mc-label">{label}</div>'
            f'<div class="mc-value">{value_pct:.1f}%</div>'
            f'<span class="mc-badge {badge_cls}">{badge_lbl}</span>'
            f'{extra}</div>'
        )

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.markdown(_mc("🎯","Overall Match",combined_score*100), unsafe_allow_html=True)
    mc2.markdown(_mc("🧠","Semantic Score",semantic_score*100), unsafe_allow_html=True)
    mc3.markdown(_mc("🔧","Skill Match",skill_score*100), unsafe_allow_html=True)
    mc4.markdown(_mc("📋","ATS Readiness",ats_score*100), unsafe_allow_html=True)

    st.markdown("<div style='margin:14px 0;'></div>", unsafe_allow_html=True)

    pdf_bytes = export_to_pdf(
        resume_name=resume_name, job_title=job_title,
        combined_score=combined_score, semantic_score=semantic_score,
        skill_score=skill_score, ats_score=ats_score,
        matched_skills=matched_skills, missing_skills=missing_skills,
        recommendations=recommendations,
        ats_checks=ats_result["checks"], ats_warnings=ats_result["warnings"],
        skill_confidences=skill_confidences,
        analysis_date=history_record["date"],
    )
    st.download_button(
        label="📄 Export PDF Report", data=pdf_bytes,
        file_name=f"resume_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf",
    )
    st.markdown("---")

    (tab_dash, tab_skills_tab, tab_recs, tab_conf,
     tab_industry, tab_charts, tab_semantic, tab_preview) = st.tabs([
        "📊 Dashboard",
        "🎯 Skills Analysis",
        "🧠 Detailed Report",
        "📈 Insights",
        "🏭 Industry Insights",
        "📉 Charts",
        "🔬 Semantic Analysis",
        "📝 Resume Preview",
    ])

    with tab_dash:
        st.markdown('<div class="section-header">📊 Match Dashboard</div>', unsafe_allow_html=True)
        for lbl,score in [("Overall Match Score",combined_score),("Semantic Similarity",semantic_score),
                           ("Skill Match",skill_score),("ATS Readiness",ats_score)]:
            pct = score*100
            css = "status-ok" if pct>=80 else "status-warn" if pct>=60 else "status-bad"
            st.markdown(f"**{lbl}** — <span class='{css}'>{pct:.1f}%</span>", unsafe_allow_html=True)
            st.progress(score)
        st.markdown("---")
        st.markdown('<div class="section-header">🔍 Advanced Matching</div>', unsafe_allow_html=True)
        adv1,adv2 = st.columns(2)
        with adv1:
            exp_card = "green" if exp_status.startswith("Qualified") else "yellow" if exp_status in ("Unknown","Overqualified") else "red"
            ry_str = f"{resume_years:.0f} yrs" if resume_years else "Not found"
            rq_str = f"{required_years:.0f} yrs" if required_years else "Not specified"
            st.markdown(f'<div class="adv-card {exp_card}"><strong>💼 Experience</strong><br>Candidate: <em>{ry_str}</em> &nbsp;|&nbsp; Required: <em>{rq_str}</em><br>Status: <span class="{exp_css}">{exp_status}</span></div>', unsafe_allow_html=True)
            edu_card = "green" if edu_status.startswith("Meets") else "yellow" if required_edu_rank==0 else "red"
            st.markdown(f'<div class="adv-card {edu_card}"><strong>🎓 Education</strong><br>Candidate: <em>{resume_edu_name}</em> &nbsp;|&nbsp; Required: <em>{required_edu_name if required_edu_rank else "Not specified"}</em><br>Status: <span class="{edu_css}">{edu_status}</span></div>', unsafe_allow_html=True)
        with adv2:
            sal_str = f"${salary_range[0]:.0f}K – ${salary_range[1]:.0f}K" if salary_range else "Not specified"
            st.markdown(f'<div class="adv-card blue"><strong>💰 Salary Range</strong><br><em>{sal_str}</em></div>', unsafe_allow_html=True)
            loc_card = "green" if location in ("Remote","Hybrid / Remote") else "blue"
            st.markdown(f'<div class="adv-card {loc_card}"><strong>📍 Location</strong><br><em>{location}</em></div>', unsafe_allow_html=True)
            visa_card = "yellow" if visa_needed else "green"
            visa_lbl  = "Visa sponsorship mentioned" if visa_needed else "No visa sponsorship mentioned"
            st.markdown(f'<div class="adv-card {visa_card}"><strong>🛂 Visa / Work Auth</strong><br><em>{visa_lbl}</em></div>', unsafe_allow_html=True)
        if ats_result["warnings"]:
            st.markdown("---")
            st.markdown('<div class="section-header">⚠️ ATS Compatibility Warnings</div>', unsafe_allow_html=True)
            for w in ats_result["warnings"]:
                st.warning(w)

    with tab_skills_tab:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-header">✅ Matched Skills</div>', unsafe_allow_html=True)
            if matched_skills:
                badges = "".join(f'<span class="skill-badge-green">✅ {s.title()}</span>' for s in sorted(matched_skills))
                st.markdown(f'<div style="line-height:2;">{badges}</div>', unsafe_allow_html=True)
            else:
                st.info("No skills from the database matched.")
        with c2:
            st.markdown('<div class="section-header">❌ Missing Skills</div>', unsafe_allow_html=True)
            if missing_skills:
                badges = "".join(f'<span class="skill-badge-red">❌ {s.title()}</span>' for s in sorted(missing_skills))
                st.markdown(f'<div style="line-height:2;">{badges}</div>', unsafe_allow_html=True)
            else:
                st.success("All required skills are present!")
        if bonus_skills:
            st.markdown("---")
            with st.expander("⭐ Bonus skills in your resume (not required by job)"):
                badges = "".join(f'<span class="skill-badge-yellow">• {s.title()}</span>' for s in sorted(bonus_skills))
                st.markdown(f'<div style="line-height:2;">{badges}</div>', unsafe_allow_html=True)

    with tab_recs:
        st.markdown('<div class="section-header">💡 Personalised Recommendations</div>', unsafe_allow_html=True)
        if not recommendations:
            st.success("🎉 Your resume looks great! No major recommendations at this time.")
        else:
            plabels = {"high":"High Priority","medium":"Medium Priority","low":"Low Priority"}
            for i,rec in enumerate(recommendations, 1):
                prio_cls = f"prio-{rec['priority']}"
                st.markdown(
                    f'<div class="rec-card rec-{rec["priority"]}">'
                    f'<strong>{rec["icon"]} {i}. {rec["title"]}</strong>'
                    f' &nbsp;<span class="{prio_cls}">({plabels[rec["priority"]]})</span>'
                    f'<br><span style="font-size:0.9rem;">{rec["detail"]}</span></div>',
                    unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<div class="section-header">📋 ATS Compatibility Checklist</div>', unsafe_allow_html=True)
        for label,passed,detail in ats_result["checks"]:
            icon   = "✅" if passed else "❌"
            colour = "ats-pass" if passed else "ats-fail"
            st.markdown(f'<div class="ats-check"><span class="{colour}">{icon} <strong>{label}</strong></span> — {detail}</div>', unsafe_allow_html=True)

    with tab_conf:
        st.markdown('<div class="section-header">📈 Skill Match Confidence</div>', unsafe_allow_html=True)
        st.markdown("Confidence shows how prominently each skill appears in your resume. High = skill appears 3+ times or in a dedicated skills section.")
        if skill_confidences:
            chips_html = ""
            for sk,(cp,lv) in sorted(skill_confidences.items(), key=lambda x: -x[1][0]):
                chips_html += f'<span class="skill-chip chip-{lv}">{sk.title()} {cp}%</span>'
            st.markdown(chips_html, unsafe_allow_html=True)
            st.markdown("---")
            for sk,(cp,lv) in sorted(skill_confidences.items(), key=lambda x: -x[1][0]):
                level_label = "🟢 High" if lv=="high" else "🟡 Medium" if lv=="medium" else "🔴 Low"
                ca,cb = st.columns([3,1])
                ca.markdown(f"**{sk.title()}**")
                cb.markdown(f'<span class="conf-{lv}">{level_label} ({cp}%)</span>', unsafe_allow_html=True)
                st.progress(cp/100)
            st.markdown("---")
            st.plotly_chart(create_confidence_chart(skill_confidences), use_container_width=True)
        else:
            st.info("No matched skills to show confidence scores for.")

    with tab_industry:
        st.markdown('<div class="section-header">🏭 Industry Insights & Competitive Analysis</div>', unsafe_allow_html=True)
        st.markdown("Trending industry skills currently missing from your resume.")
        if industry_trends:
            for item in industry_trends:
                st.markdown(
                    f'<div class="rec-card rec-medium"><strong>📌 {item["skill"].title()}</strong>'
                    f' &nbsp;<span class="prio-medium">({item["category"]})</span><br>'
                    f'<span>Top in-demand skill in your industry. '
                    f'&nbsp;<a href="{item["resource"]}" target="_blank" style="color:#3B82F6;">📚 Learn more →</a></span></div>',
                    unsafe_allow_html=True)
        else:
            st.success("🎉 Your resume already covers all the top trending skills for this role!")
        st.markdown("---")
        st.markdown('<div class="section-header">📊 Skills by Industry Category</div>', unsafe_allow_html=True)
        for cat,skills in INDUSTRY_TRENDING_SKILLS.items():
            have = [s for s in skills if s in resume_skills]
            need = [s for s in skills if s in job_skills and s not in resume_skills]
            with st.expander(f"**{cat}** — {len(have)} of {len(skills)} trending skills"):
                if have: st.markdown("✅ **You have:** " + ", ".join(s.title() for s in have))
                if need: st.markdown("❌ **Consider adding:** " + ", ".join(s.title() for s in need))
                if not have and not need: st.markdown("*No overlapping skills in this category.*")

    with tab_charts:
        cc1,cc2 = st.columns(2)
        with cc1: st.plotly_chart(create_skill_chart(len(matched_skills),len(missing_skills),len(bonus_skills)), use_container_width=True)
        with cc2: st.plotly_chart(create_score_chart(semantic_score,skill_score,combined_score), use_container_width=True)
        st.caption(f"Matched: {len(matched_skills)} skill(s) &nbsp;|&nbsp; Missing: {len(missing_skills)} skill(s) &nbsp;|&nbsp; Bonus: {len(bonus_skills)} skill(s)")

    with tab_semantic:
        st.markdown('<div class="section-header">🔬 Deep-Learning Similarity Breakdown</div>', unsafe_allow_html=True)
        st.markdown("**Overall semantic similarity between resume and job description:**")
        st.progress(semantic_score)
        st.caption(f"{semantic_score*100:.1f}% — " + (
            "Strong match 🟢" if semantic_score >= STRONG_MATCH_THRESHOLD
            else "Moderate match 🟡" if semantic_score >= MODERATE_MATCH_THRESHOLD
            else "Weak match 🔴"))
        st.markdown("---")
        st.markdown("**Skill coverage (required skills found in resume):**")
        st.progress(skill_score)
        st.caption(f"{skill_score*100:.1f}% — {len(matched_skills)}/{len(job_skills)} required skills matched")
        st.markdown("---")
        st.markdown("**Combined score (60% semantic + 40% skill match):**")
        st.progress(combined_score)
        st.caption(f"{combined_score*100:.1f}%")
        st.markdown("---")
        st.info("The semantic score is computed using the `all-MiniLM-L6-v2` transformer model from Hugging Face. It measures *meaning* similarity, not just keyword overlap.")

    with tab_preview:
        st.markdown('<div class="section-header">📝 Extracted Resume Text</div>', unsafe_allow_html=True)
        st.text_area("", value=resume_text, height=400, disabled=True)

    st.markdown("---")
    st.markdown('<div class="section-header">💾 Save This Analysis</div>', unsafe_allow_html=True)
    sc1,sc2 = st.columns([3,1])
    with sc1:
        save_label = st.text_input("Label for saved analysis", value=f"{resume_name} – {job_title[:30]}", key="save_label_input")
    with sc2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Save", key="save_analysis_btn"):
            st.session_state.saved_analyses[save_label] = history_record
            st.success(f"Saved as: **{save_label}**")

else:
    st.markdown(
        """
        <div class="fade-in" style="background:#1C2128;border-radius:14px;padding:32px;border:1px solid #30363D;margin-top:16px;">
        <h3 style="color:#3B82F6;margin-top:0;">👈 Get Started</h3>
        <p style="color:#9CA3AF;">Upload a resume PDF and paste a job description in the sidebar to get started!</p>
        <hr style="border-color:#30363D;">
        <h4 style="color:#E5E7EB;">How it works</h4>
        <ol style="color:#9CA3AF;line-height:2;">
        <li><strong style="color:#E5E7EB;">Upload</strong> your resume as a PDF</li>
        <li><strong style="color:#E5E7EB;">Paste</strong> the job description</li>
        <li>The app uses a <strong style="color:#3B82F6;">Hugging Face transformer model</strong> to measure semantic similarity</li>
        <li>It also <strong style="color:#E5E7EB;">extracts and compares technical skills</strong> automatically</li>
        <li>You get a detailed <strong style="color:#10B981;">match score with recommendations</strong></li>
        <li><strong style="color:#E5E7EB;">Advanced metrics</strong> — experience years, education level, salary range, location</li>
        <li><strong style="color:#E5E7EB;">Beautiful dark-theme charts</strong> — skill breakdown &amp; score comparison</li>
        <li><strong style="color:#FBBF24;">ATS Score</strong> — compatibility check with detailed pass/fail breakdown</li>
        <li><strong style="color:#E5E7EB;">Recommendations</strong> — personalised, actionable improvement tips (top 3–5)</li>
        <li><strong style="color:#E5E7EB;">Confidence Scores</strong> — how prominently each matched skill appears</li>
        <li><strong style="color:#E5E7EB;">Industry Insights</strong> — top trending skills you're missing with learning links</li>
        <li><strong style="color:#E5E7EB;">History</strong> — track all your analyses over time</li>
        <li><strong style="color:#E5E7EB;">Compare</strong> — side-by-side comparison of saved analyses</li>
        <li><strong style="color:#E5E7EB;">Bookmarks</strong> — save favourite job descriptions for quick access</li>
        <li><strong style="color:#EF4444;">PDF Export</strong> — one-click professional report download</li>
        </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Application History
st.markdown("---")
st.markdown('<div class="section-header">📜 Application History</div>', unsafe_allow_html=True)
if not st.session_state.history:
    st.info("No history yet. Run an analysis to start tracking your applications.")
else:
    hist_search = st.text_input("🔍 Search history", placeholder="Filter by job title, company, or resume name…", key="hist_search")
    filtered = [r for r in st.session_state.history if not hist_search or hist_search.lower() in json.dumps(r).lower()]
    if not filtered:
        st.info("No records match your search.")
    else:
        for idx,record in enumerate(filtered):
            pct   = record["overall_score"]
            badge = "🟢" if pct>=80 else "🟡" if pct>=60 else "🔴"
            ca,cb,cc = st.columns([5,2,1])
            with ca:
                st.markdown(f"**{record['resume_name']}** → {record['job_title']} <span style='color:#9CA3AF;font-size:0.85rem;'>({record['company']})</span>", unsafe_allow_html=True)
                st.caption(f"📅 {record['date']}")
            with cb:
                st.markdown(f"{badge} **{pct}%** match &nbsp;|&nbsp; ATS: {record['ats_score']}%")
            with cc:
                if st.button("🗑️", key=f"del_hist_{idx}", help="Delete this record"):
                    st.session_state.history.pop(st.session_state.history.index(record))
                    st.rerun()
            st.markdown("<hr class='dark-divider'>", unsafe_allow_html=True)
    if st.button("🗑️ Clear All History", key="clear_history"):
        st.session_state.history = []
        st.rerun()

# Compare Saved Resumes
if st.session_state.saved_analyses:
    st.markdown("---")
    st.markdown('<div class="section-header">📊 Compare Saved Analyses</div>', unsafe_allow_html=True)
    saved_labels = list(st.session_state.saved_analyses.keys())
    cl,cr = st.columns(2)
    with cl: left_label  = st.selectbox("Select first analysis",  saved_labels, key="cmp_left")
    with cr:
        right_opts  = [l for l in saved_labels if l != left_label] or saved_labels
        right_label = st.selectbox("Select second analysis", right_opts, key="cmp_right")
    if left_label and right_label and left_label in st.session_state.saved_analyses and right_label in st.session_state.saved_analyses:
        la = st.session_state.saved_analyses[left_label]
        ra = st.session_state.saved_analyses[right_label]
        metrics = [
            ("🎯 Overall Match", f"{la['overall_score']}%", f"{ra['overall_score']}%"),
            ("🧠 Semantic Score", f"{la['semantic_score']}%", f"{ra['semantic_score']}%"),
            ("🔧 Skill Match",    f"{la['skill_score']}%",   f"{ra['skill_score']}%"),
            ("📋 ATS Score",      f"{la['ats_score']}%",     f"{ra['ats_score']}%"),
            ("✅ Matched Skills", str(len(la['matched_skills'])), str(len(ra['matched_skills']))),
            ("❌ Missing Skills", str(len(la['missing_skills'])), str(len(ra['missing_skills']))),
        ]
        h1,h2,h3 = st.columns(3)
        h1.markdown("**Metric**"); h2.markdown(f"**{left_label[:22]}**"); h3.markdown(f"**{right_label[:22]}**")
        st.markdown("<hr class='dark-divider'>", unsafe_allow_html=True)
        for lbl,lv,rv in metrics:
            c1,c2,c3 = st.columns(3)
            c1.markdown(lbl); c2.markdown(lv); c3.markdown(rv)
        rm1,rm2 = st.columns(2)
        if rm1.button(f"🗑️ Remove '{left_label[:20]}'",  key="rm_left"):
            del st.session_state.saved_analyses[left_label];  st.rerun()
        if rm2.button(f"🗑️ Remove '{right_label[:20]}'", key="rm_right"):
            del st.session_state.saved_analyses[right_label]; st.rerun()

# Bookmark Management
if st.session_state.bookmarks:
    st.markdown("---")
    st.markdown('<div class="section-header">🔖 Job Bookmarks</div>', unsafe_allow_html=True)
    for idx,bm in enumerate(st.session_state.bookmarks):
        bc1,bc2 = st.columns([5,1])
        with bc1:
            with st.expander(f"📌 {bm['title']}"):
                st.text_area("Job Description", value=bm["description"], height=150, disabled=True, key=f"bm_preview_{idx}")
        with bc2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if st.button("🗑️ Remove", key=f"rm_bm_{idx}"):
                st.session_state.bookmarks.pop(idx)
                st.rerun()
