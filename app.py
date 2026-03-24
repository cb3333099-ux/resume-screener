import streamlit as st
import pypdf
from io import BytesIO

st.set_page_config(page_title="Resume Screener", layout="wide")

st.title("📄 Simple Resume Screener")

# Sidebar
with st.sidebar:
    st.header("Upload")
    resume_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    job_description = st.text_area("Paste Job Description", height=200)

# Main content
if resume_file and job_description:
    # Extract text from PDF
    pdf_reader = pypdf.PdfReader(resume_file)
    resume_text = ""
    for page in pdf_reader.pages:
        resume_text += page.extract_text()
    
    st.success("✅ Resume uploaded!")
    
    # Simple keyword matching
    resume_lower = resume_text.lower()
    job_lower = job_description.lower()
    
    # Extract keywords from job description
    keywords = [word.strip() for word in job_lower.split() if len(word) > 3]
    keywords = list(set(keywords))[:20]  # Top 20 unique keywords
    
    # Count matches
    matches = sum(1 for keyword in keywords if keyword in resume_lower)
    match_percentage = (matches / len(keywords) * 100) if keywords else 0
    
    # Display results
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Match Score", f"{match_percentage:.1f}%")
    
    with col2:
        st.metric("Keywords Found", f"{matches}/{len(keywords)}")
    
    # Show details
    st.subheader("📋 Analysis")
    
    matching = [k for k in keywords if k in resume_lower]
    missing = [k for k in keywords if k not in resume_lower]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("✅ **Found Keywords:**")
        if matching:
            for word in matching[:10]:
                st.write(f"  • {word}")
        else:
            st.write("  None")
    
    with col2:
        st.write("❌ **Missing Keywords:**")
        if missing:
            for word in missing[:10]:
                st.write(f"  • {word}")
        else:
            st.write("  None")
    
    # Show resume preview
    with st.expander("📝 Resume Text Preview"):
        st.text(resume_text[:1000] + "...")

else:
    st.info("👈 Upload a resume and paste a job description to get started!")