import streamlit as st
import pypdf
from io import BytesIO

st.set_page_config(page_title="AI Resume Screener", layout="wide")

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

# Scoring weights (must sum to 1.0)
SEMANTIC_WEIGHT = 0.6
SKILL_WEIGHT = 0.4

# Thresholds for labelling the semantic score
STRONG_MATCH_THRESHOLD = 0.7
MODERATE_MATCH_THRESHOLD = 0.45


def extract_skills(text: str) -> list[str]:
    """Return skills from SKILLS_DB that appear in *text*.

    Uses simple substring matching, so multi-word skills (e.g. "machine learning")
    are found correctly. Single-word skills may occasionally match inside longer
    words (e.g. "java" inside "javascript"); the skills database is designed to
    minimise such overlaps where possible.
    """
    text_lower = text.lower()
    return [skill for skill in SKILLS_DB if skill in text_lower]


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
    # Compute scores
    # ------------------------------------------------------------------
    semantic_score = semantic_similarity(model, resume_text, job_description)

    resume_skills = set(extract_skills(resume_text))
    job_skills = set(extract_skills(job_description))

    matched_skills = resume_skills & job_skills
    missing_skills = job_skills - resume_skills

    skill_score = (
        len(matched_skills) / len(job_skills) if job_skills else 0.0
    )

    # Weighted combined score: SEMANTIC_WEIGHT semantic + SKILL_WEIGHT skill match
    combined_score = SEMANTIC_WEIGHT * semantic_score + SKILL_WEIGHT * skill_score

    # ------------------------------------------------------------------
    # Top-level metrics
    # ------------------------------------------------------------------
    st.success("✅ Analysis complete!")
    m1, m2, m3 = st.columns(3)
    m1.metric("🎯 Overall Match", f"{combined_score * 100:.1f}%")
    m2.metric("🧠 Semantic Score", f"{semantic_score * 100:.1f}%")
    m3.metric("🔧 Skill Match", f"{skill_score * 100:.1f}%")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------
    tab_skills, tab_semantic, tab_preview = st.tabs(
        ["🎯 Skills Analysis", "🧠 Semantic Analysis", "📝 Resume Preview"]
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
                f"Consider adding experience with: "
                + ", ".join(f"**{s}**" for s in sorted(missing_skills))
            )
        else:
            st.success(
                "Great match! Your resume covers all the skills found in the job description."
            )

        # Skills found in resume but not in job description (bonus skills)
        bonus_skills = resume_skills - job_skills
        if bonus_skills:
            with st.expander("🌟 Bonus skills in your resume (not required by job)"):
                for skill in sorted(bonus_skills):
                    st.write(f"• {skill}")

    # ---- Semantic Analysis ----
    with tab_semantic:
        st.subheader("🧠 Deep-Learning Similarity Breakdown")

        # Gauge-style progress bars
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
        """
    )
