import re
import streamlit as st
import pypdf
from io import BytesIO
import plotly.graph_objects as go

st.set_page_config(page_title="AI Resume Screener", layout="wide", page_icon="🤖")

# ---------------------------------------------------------------------------
# Custom CSS – professional look with color-coded badges
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
        letter-spacing: 0.03em;
    }
    .badge-green  { background-color: #28a745; color: #fff; }
    .badge-yellow { background-color: #ffc107; color: #212529; }
    .badge-red    { background-color: #dc3545; color: #fff; }

    .status-ok      { color: #28a745; font-weight: 700; }
    .status-warn    { color: #e6a817; font-weight: 700; }
    .status-bad     { color: #dc3545; font-weight: 700; }

    .adv-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 8px;
        border-left: 4px solid #6c757d;
    }
    .adv-card.green  { border-left-color: #28a745; }
    .adv-card.yellow { border-left-color: #ffc107; }
    .adv-card.red    { border-left-color: #dc3545; }
    .adv-card.blue   { border-left-color: #17a2b8; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🤖 AI Resume Screener")
st.markdown("*Powered by Hugging Face sentence-transformers — semantic AI/ML matching*")

# ---------------------------------------------------------------------------
# Common skills database
# ---------------------------------------------------------------------------
SKILLS_DB = [
    # Languages
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
    "kotlin", "swift", "ruby", "php", "scala", "r", "matlab", "bash", "shell",
    # Web / Frontend
    "react", "angular", "vue", "next.js", "html", "css", "sass", "tailwind",
    "bootstrap", "webpack", "vite",
    # Backend / APIs
    "node.js", "django", "flask", "fastapi", "spring", "express", "graphql",
    "rest", "grpc",
    # Databases
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "cassandra", "dynamodb", "sqlite",
    # Cloud / DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "github actions", "ci/cd", "linux", "nginx",
    # Data / AI
    "machine learning", "deep learning", "nlp", "tensorflow", "pytorch",
    "scikit-learn", "pandas", "numpy", "spark", "hadoop", "tableau", "power bi",
    # Practices
    "agile", "scrum", "microservices", "git", "jira", "confluence",
]

# Education levels (term → numeric rank)
EDUCATION_LEVELS = {
    "ph.d": 5, "phd": 5, "doctorate": 5, "doctoral": 5,
    "master": 4, "m.s.": 4, "m.sc": 4, "mba": 4, "m.eng": 4,
    "bachelor": 3, "b.s.": 3, "b.sc": 3, "b.eng": 3, "b.tech": 3, "undergraduate": 3,
    "associate": 2,
    "high school": 1, "diploma": 1, "ged": 1,
}

# Scoring weights (must sum to 1.0)
SEMANTIC_WEIGHT = 0.6
SKILL_WEIGHT = 0.4

# Thresholds for labelling the semantic score
STRONG_MATCH_THRESHOLD = 0.7
MODERATE_MATCH_THRESHOLD = 0.45

# ATS readiness blending weights (must sum to 1.0)
ATS_COMBINED_WEIGHT = 0.85
ATS_SKILL_COVERAGE_WEIGHT = 0.15

# ---------------------------------------------------------------------------
# Helper – badge HTML
# ---------------------------------------------------------------------------

def get_color_badge(score: float) -> tuple[str, str, str]:
    """Return (css_class, label, emoji) based on *score* in 0–1 range."""
    pct = score * 100
    if pct >= 80:
        return "badge-green", "Excellent Fit", "🟢"
    if pct >= 60:
        return "badge-yellow", "Good Fit", "🟡"
    return "badge-red", "Poor Fit", "🔴"


def render_badge(score: float) -> str:
    """Return an HTML badge string for a given score."""
    css, label, _ = get_color_badge(score)
    return f'<span class="badge {css}">{label} — {score * 100:.1f}%</span>'


def stars(score: float) -> str:
    """Return a star-rating string (★☆) for a 0–1 score."""
    filled = round(score * 5)
    return "★" * filled + "☆" * (5 - filled)

# ---------------------------------------------------------------------------
# Skills extraction
# ---------------------------------------------------------------------------

def extract_skills(text: str) -> list[str]:
    """Return skills from SKILLS_DB that appear in *text*."""
    text_lower = text.lower()
    return [skill for skill in SKILLS_DB if skill in text_lower]

# ---------------------------------------------------------------------------
# ML model
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def load_model():
    """Load sentence-transformer model once and cache it."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


def semantic_similarity(model, text_a: str, text_b: str) -> float:
    """Return cosine similarity (0–1) between two texts."""
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    embeddings = model.encode([text_a, text_b])
    score = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return float(np.clip(score, 0.0, 1.0))

# ---------------------------------------------------------------------------
# Advanced matching helpers
# ---------------------------------------------------------------------------

def extract_years_experience(text: str) -> float | None:
    """Return the first years-of-experience figure found in *text*, or None."""
    patterns = [
        r'(\d+)\+?\s*(?:years?|yrs?)[\s\-]+(?:of[\s\-]+)?(?:experience|exp\b)',
        r'(?:experience|exp\b)[\s\-]+(?:of[\s\-]+)?(\d+)\+?\s*(?:years?|yrs?)',
        r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:in|with|using)\b',
        r'minimum\s+(?:of\s+)?(\d+)\+?\s*(?:years?|yrs?)',
        r'at\s+least\s+(\d+)\+?\s*(?:years?|yrs?)',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return None


def extract_education_level(text: str) -> tuple[str, int]:
    """Return (human-readable name, numeric rank) of the highest education found."""
    text_lower = text.lower()
    best_name, best_rank = "Not specified", 0
    for term, rank in EDUCATION_LEVELS.items():
        if term in text_lower and rank > best_rank:
            best_name, best_rank = term.title(), rank
    return best_name, best_rank


def extract_salary_range(text: str) -> tuple[float, float] | None:
    """Return (min_k, max_k) in thousands, or None if no range found."""
    patterns = [
        r'\$\s*(\d+(?:\.\d+)?)\s*[Kk]\s*[-–—to]+\s*\$?\s*(\d+(?:\.\d+)?)\s*[Kk]',
        r'\$\s*(\d{3,6}(?:,\d{3})?)\s*[-–—to]+\s*\$?\s*(\d{3,6}(?:,\d{3})?)',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            low  = float(m.group(1).replace(',', ''))
            high = float(m.group(2).replace(',', ''))
            if low  > 1000: low  /= 1000
            if high > 1000: high /= 1000
            return low, high
    return None


def extract_location(text: str) -> str:
    """Extract work-location requirement from *text*."""
    text_lower = text.lower()
    has_remote = "remote" in text_lower
    has_hybrid = "hybrid" in text_lower
    has_onsite = any(kw in text_lower for kw in ("on-site", "onsite", "in-office", "in office"))
    if has_remote and has_hybrid:
        return "Hybrid / Remote"
    if has_remote:
        return "Remote"
    if has_hybrid:
        return "Hybrid"
    if has_onsite:
        return "On-site"
    m = re.search(r'(?:location|based in|office in)\s*[:\-]?\s*([A-Z][a-zA-Z\s]+(?:,\s*[A-Z]{2})?)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return "Not specified"


def calculate_experience_match(resume_years: float | None, required_years: float | None) -> tuple[str, str]:
    """Return (status_label, css_class) comparing resume vs required years."""
    if resume_years is None or required_years is None:
        return "Unknown", "status-warn"
    if resume_years >= required_years * 1.5:
        return "Overqualified", "status-warn"
    if resume_years >= required_years:
        return "Qualified ✔", "status-ok"
    return "Underqualified", "status-bad"

# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def create_skill_chart(matched: int, missing: int, bonus: int) -> go.Figure:
    """Donut chart – skill breakdown."""
    labels = ["Matched", "Missing", "Bonus"]
    values = [matched, missing, bonus]
    colors = ["#28a745", "#dc3545", "#17a2b8"]
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        marker=dict(colors=colors, line=dict(color="#fff", width=2)),
        textinfo="label+percent",
        hovertemplate="%{label}: %{value} skill(s)<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Skill Breakdown", font=dict(size=16)),
        showlegend=True,
        height=340,
        margin=dict(t=50, b=10, l=10, r=10),
    )
    return fig


def create_score_chart(semantic: float, skill: float, combined: float) -> go.Figure:
    """Horizontal bar chart – score comparison."""
    scores = [semantic * 100, skill * 100, combined * 100]
    categories = ["Semantic Similarity", "Skill Match", "Overall Score"]
    bar_colors = [
        "#28a745" if s >= 80 else "#ffc107" if s >= 60 else "#dc3545"
        for s in scores
    ]
    fig = go.Figure(go.Bar(
        x=scores,
        y=categories,
        orientation="h",
        marker_color=bar_colors,
        text=[f"{s:.1f}%" for s in scores],
        textposition="outside",
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Score Breakdown", font=dict(size=16)),
        xaxis=dict(range=[0, 115], ticksuffix="%", showgrid=True, gridcolor="#eee"),
        yaxis=dict(autorange="reversed"),
        height=240,
        margin=dict(t=50, b=20, l=20, r=60),
        plot_bgcolor="white",
    )
    return fig

# ---------------------------------------------------------------------------
# Sidebar – inputs
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("📂 Inputs")
    resume_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    job_description = st.text_area("Paste Job Description", height=250)
    st.markdown("---")
    st.caption("Model: `all-MiniLM-L6-v2` (Hugging Face, free, no API key)")

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
if resume_file and job_description:
    # Extract text from PDF
    pdf_reader = pypdf.PdfReader(BytesIO(resume_file.read()))
    resume_text = "\n".join(
        page.extract_text() or "" for page in pdf_reader.pages
    )

    if not resume_text.strip():
        st.error("Could not extract text from the PDF. Please upload a text-based PDF.")
        st.stop()

    # Load model with progress indicator
    with st.spinner("🧠 Loading AI model (first run may take ~30 s)…"):
        model = load_model()

    # ------------------------------------------------------------------
    # Compute core scores
    # ------------------------------------------------------------------
    semantic_score = semantic_similarity(model, resume_text, job_description)

    resume_skills = set(extract_skills(resume_text))
    job_skills    = set(extract_skills(job_description))

    matched_skills = resume_skills & job_skills
    missing_skills = job_skills - resume_skills
    bonus_skills   = resume_skills - job_skills

    skill_score = len(matched_skills) / len(job_skills) if job_skills else 0.0

    # Weighted combined score
    combined_score = SEMANTIC_WEIGHT * semantic_score + SKILL_WEIGHT * skill_score

    # ATS readiness: penalise heavily missing skills, boost semantic alignment
    ats_score = min(
        1.0,
        ATS_COMBINED_WEIGHT * combined_score
        + ATS_SKILL_COVERAGE_WEIGHT * (1 - len(missing_skills) / max(len(job_skills), 1)),
    )

    # ------------------------------------------------------------------
    # Advanced matching
    # ------------------------------------------------------------------
    resume_years   = extract_years_experience(resume_text)
    required_years = extract_years_experience(job_description)
    exp_status, exp_css = calculate_experience_match(resume_years, required_years)

    resume_edu_name,   resume_edu_rank   = extract_education_level(resume_text)
    required_edu_name, required_edu_rank = extract_education_level(job_description)
    if required_edu_rank == 0:
        edu_status, edu_css = "Not specified", "status-warn"
    elif resume_edu_rank >= required_edu_rank:
        edu_status, edu_css = "Meets requirement ✔", "status-ok"
    else:
        edu_status, edu_css = "Does not meet requirement", "status-bad"

    salary_range = extract_salary_range(job_description)
    location     = extract_location(job_description)
    visa_needed  = any(kw in job_description.lower() for kw in ("visa sponsorship", "work permit", "work authorization", "authorized to work"))

    # ------------------------------------------------------------------
    # Top-level header metrics
    # ------------------------------------------------------------------
    st.success("✅ Analysis complete!")

    badge_css, badge_label, badge_emoji = get_color_badge(combined_score)
    st.markdown(
        f"### Overall Match &nbsp; {render_badge(combined_score)} &nbsp; {stars(combined_score)}",
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🎯 Overall Match",  f"{combined_score * 100:.1f}%")
    col2.metric("🧠 Semantic Score", f"{semantic_score * 100:.1f}%")
    col3.metric("🔧 Skill Match",    f"{skill_score * 100:.1f}%")
    col4.metric("📋 ATS Readiness",  f"{ats_score * 100:.1f}%")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------
    tab_dash, tab_skills, tab_charts, tab_semantic, tab_preview = st.tabs([
        "📊 Dashboard",
        "🎯 Skills Analysis",
        "📈 Charts",
        "🧠 Semantic Analysis",
        "📝 Resume Preview",
    ])

    # ---- Dashboard ----
    with tab_dash:
        st.subheader("📊 Match Dashboard")

        # Score progress bars with color labels
        pct = combined_score * 100
        label_css = "status-ok" if pct >= 80 else "status-warn" if pct >= 60 else "status-bad"
        st.markdown(f"**Overall Match Score** — <span class='{label_css}'>{pct:.1f}%</span>", unsafe_allow_html=True)
        st.progress(combined_score)

        pct_sem = semantic_score * 100
        sem_css = "status-ok" if pct_sem >= 80 else "status-warn" if pct_sem >= 60 else "status-bad"
        st.markdown(f"**Semantic Similarity** — <span class='{sem_css}'>{pct_sem:.1f}%</span>", unsafe_allow_html=True)
        st.progress(semantic_score)

        pct_sk = skill_score * 100
        sk_css = "status-ok" if pct_sk >= 80 else "status-warn" if pct_sk >= 60 else "status-bad"
        st.markdown(f"**Skill Match** — <span class='{sk_css}'>{pct_sk:.1f}%</span>", unsafe_allow_html=True)
        st.progress(skill_score)

        pct_ats = ats_score * 100
        ats_css = "status-ok" if pct_ats >= 80 else "status-warn" if pct_ats >= 60 else "status-bad"
        st.markdown(f"**ATS Readiness** — <span class='{ats_css}'>{pct_ats:.1f}%</span>", unsafe_allow_html=True)
        st.progress(ats_score)

        st.markdown("---")
        st.subheader("🔍 Advanced Matching")

        adv1, adv2 = st.columns(2)

        with adv1:
            # Experience card
            if exp_status.startswith("Qualified"):
                exp_card_css = "green"
            elif exp_status in ("Unknown", "Overqualified"):
                exp_card_css = "yellow"
            else:
                exp_card_css = "red"
            resume_yrs_str   = f"{resume_years:.0f} yrs"   if resume_years   else "Not found"
            required_yrs_str = f"{required_years:.0f} yrs" if required_years else "Not specified"
            st.markdown(
                f"""<div class="adv-card {exp_card_css}">
                    <strong>💼 Experience</strong><br>
                    Candidate: <em>{resume_yrs_str}</em> &nbsp;|&nbsp; Required: <em>{required_yrs_str}</em><br>
                    Status: <span class="{exp_css}">{exp_status}</span>
                </div>""",
                unsafe_allow_html=True,
            )

            # Education card
            edu_card_css = "green" if edu_status.startswith("Meets") else "yellow" if required_edu_rank == 0 else "red"
            st.markdown(
                f"""<div class="adv-card {edu_card_css}">
                    <strong>🎓 Education</strong><br>
                    Candidate: <em>{resume_edu_name}</em> &nbsp;|&nbsp; Required: <em>{required_edu_name if required_edu_rank else "Not specified"}</em><br>
                    Status: <span class="{edu_css}">{edu_status}</span>
                </div>""",
                unsafe_allow_html=True,
            )

        with adv2:
            # Salary card
            if salary_range:
                lo, hi = salary_range
                salary_str = f"${lo:.0f}K – ${hi:.0f}K"
            else:
                salary_str = "Not specified"
            st.markdown(
                f"""<div class="adv-card blue">
                    <strong>💰 Salary Range</strong><br>
                    <em>{salary_str}</em>
                </div>""",
                unsafe_allow_html=True,
            )

            # Location card
            loc_card_css = "green" if location in ("Remote", "Hybrid / Remote") else "blue"
            st.markdown(
                f"""<div class="adv-card {loc_card_css}">
                    <strong>📍 Location</strong><br>
                    <em>{location}</em>
                </div>""",
                unsafe_allow_html=True,
            )

            # Visa card
            visa_card_css = "yellow" if visa_needed else "green"
            visa_label    = "Visa sponsorship mentioned" if visa_needed else "No visa sponsorship mentioned"
            st.markdown(
                f"""<div class="adv-card {visa_card_css}">
                    <strong>🛂 Visa / Work Auth</strong><br>
                    <em>{visa_label}</em>
                </div>""",
                unsafe_allow_html=True,
            )

    # ---- Skills Analysis ----
    with tab_skills:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("✅ Matched Skills")
            if matched_skills:
                for skill in sorted(matched_skills):
                    st.write(f"✅ {skill}")
            else:
                st.info("No skills from the database matched.")

        with col2:
            st.subheader("❌ Missing Skills")
            if missing_skills:
                for skill in sorted(missing_skills):
                    st.write(f"❌ {skill}")
            else:
                st.success("All required skills are present!")

        st.markdown("---")
        st.subheader("📋 Recommendations")
        if missing_skills:
            st.warning(
                "Consider adding experience with: "
                + ", ".join(f"**{s}**" for s in sorted(missing_skills))
            )
        else:
            st.success(
                "Great match! Your resume covers all the skills found in the job description."
            )

        if bonus_skills:
            with st.expander("🌟 Bonus skills in your resume (not required by job)"):
                for skill in sorted(bonus_skills):
                    st.write(f"• {skill}")

    # ---- Charts ----
    with tab_charts:
        chart_col1, chart_col2 = st.columns([1, 1])

        with chart_col1:
            st.plotly_chart(
                create_skill_chart(len(matched_skills), len(missing_skills), len(bonus_skills)),
                use_container_width=True,
            )

        with chart_col2:
            st.plotly_chart(
                create_score_chart(semantic_score, skill_score, combined_score),
                use_container_width=True,
            )

        st.markdown("---")
        st.caption(
            f"Matched: {len(matched_skills)} skill(s) &nbsp;|&nbsp; "
            f"Missing: {len(missing_skills)} skill(s) &nbsp;|&nbsp; "
            f"Bonus: {len(bonus_skills)} skill(s)"
        )

    # ---- Semantic Analysis ----
    with tab_semantic:
        st.subheader("🧠 Deep-Learning Similarity Breakdown")

        st.markdown("**Overall semantic similarity between resume and job description:**")
        st.progress(semantic_score)
        st.caption(
            f"{semantic_score * 100:.1f}% — "
            + (
                "Strong match 🟢" if semantic_score >= STRONG_MATCH_THRESHOLD
                else "Moderate match 🟡" if semantic_score >= MODERATE_MATCH_THRESHOLD
                else "Weak match 🔴"
            )
        )

        st.markdown("---")
        st.markdown("**Skill coverage (required skills found in resume):**")
        st.progress(skill_score)
        st.caption(f"{skill_score * 100:.1f}% — {len(matched_skills)}/{len(job_skills)} required skills matched")

        st.markdown("---")
        st.markdown("**Combined score (60 % semantic + 40 % skill match):**")
        st.progress(combined_score)
        st.caption(f"{combined_score * 100:.1f}%")

        st.markdown("---")
        st.info(
            "The semantic score is computed using the `all-MiniLM-L6-v2` transformer model "
            "from Hugging Face. It measures *meaning* similarity, not just keyword overlap."
        )

    # ---- Resume Preview ----
    with tab_preview:
        st.subheader("📝 Extracted Resume Text")
        st.text_area("", value=resume_text, height=400, disabled=True)

else:
    st.info("👈 Upload a resume PDF and paste a job description in the sidebar to get started!")
    st.markdown(
        """
        ### How it works
        1. **Upload** your resume as a PDF
        2. **Paste** the job description
        3. The app uses a **Hugging Face transformer model** to measure semantic similarity
        4. It also **extracts and compares technical skills** automatically
        5. You get a detailed **match score with recommendations**
        6. **Advanced metrics** — experience years, education level, salary range, location
        7. **Beautiful charts** — skill breakdown donut chart, score comparison bar chart
        """
    )
