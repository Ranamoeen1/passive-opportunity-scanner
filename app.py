import streamlit as st
import database
from models import UserProfile
from dotenv import load_dotenv
from intelligence import evaluate_opportunity, generate_application_draft

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Passive Opportunity Scanner", layout="wide", page_icon="📡")

# Initialize DB on first load
database.init_db()

def re_evaluate_existing(profile, status_placeholder=None):
    """Re-scores every opportunity already in the DB against the current profile."""
    existing = database.get_all_opportunities()
    if not existing:
        return
    for i, opp in enumerate(existing):
        if status_placeholder:
            status_placeholder.info(f"Re-evaluating {i+1}/{len(existing)}: {opp.title[:60]}...")
        try:
            ev = evaluate_opportunity(profile, opp)
            database.update_opportunity_scores(
                opp.id, ev.relevance_score, ev.reasoning,
                ev.difficulty_level, ev.is_urgent
            )
            # Auto-draft for newly high-scoring opportunities
            if ev.relevance_score >= 80 and not database.get_draft(opp.id):
                draft = generate_application_draft(profile, opp)
                database.save_draft(opp.id, draft)
        except Exception as e:
            print(f"Re-eval error for {opp.id}: {e}")

st.title("📡 Passive Opportunity Scanner")
st.markdown("Your AI career scout that finds and pre-applies to opportunities matching your profile.")

# --- SIDEBAR: User Profile ---
st.sidebar.header("👤 Your Profile")

st.sidebar.markdown("---")
uploaded_resume = st.sidebar.file_uploader("📄 Upload Resume (PDF)", type=["pdf"])
if uploaded_resume is not None:
    if st.sidebar.button("Auto-Fill Profile from Uploaded Resume"):
        with st.spinner("Analyzing uploaded resume..."):
            from resume_parser import parse_resume_file
            new_prof = parse_resume_file(uploaded_resume)
            if new_prof:
                database.save_user_profile(new_prof)
                st.sidebar.success("Profile updated from uploaded Resume!")
                status_ph = st.sidebar.empty()
                with st.spinner("Re-evaluating existing opportunities for new profile..."):
                    re_evaluate_existing(new_prof, status_ph)
                status_ph.empty()
                st.rerun()
            else:
                st.sidebar.error("Failed to parse resume.")

profile = database.get_user_profile()

with st.sidebar.form("profile_form"):
    skills_input = st.text_input("Skills (comma-separated)", value=", ".join(profile.skills) if profile else "Python, Streamlit, API")
    interests_input = st.text_input("Interests (comma-separated)", value=", ".join(profile.interests) if profile else "Remote work, AI, Automation")
    goals_input = st.text_area("Career Goals", value=profile.goals if profile else "Find freelance gigs to build portfolio.")
    experience_level = st.selectbox("Experience Level", ["Beginner", "Intermediate", "Advanced"], index=["Beginner", "Intermediate", "Advanced"].index(profile.experience_level.capitalize()) if profile else 1)
    
    submitted = st.form_submit_button("Save Profile")
    if submitted:
        new_profile = UserProfile(
            skills=[s.strip() for s in skills_input.split(",")],
            interests=[i.strip() for i in interests_input.split(",")],
            goals=goals_input,
            experience_level=experience_level.lower()
        )
        database.save_user_profile(new_profile)
        st.sidebar.success("Profile saved!")
        status_ph = st.sidebar.empty()
        with st.spinner("Re-evaluating existing opportunities for new profile..."):
            re_evaluate_existing(new_profile, status_ph)
        status_ph.empty()
        st.rerun()

# --- MAIN: Dashboard ---
if not profile:
    st.info("👈 Please set up your profile in the sidebar to start finding matching opportunities.")
else:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("🎯 Top Matches")
        min_score = st.slider("Minimum Relevance Score", 0, 100, 50, step=5)
        
        opps = database.get_opportunities(min_score=min_score)
        
        if not opps:
            st.write("No opportunities found yet. Ensure the scheduler is running (`python scheduler.py`).")
        else:
            for opp in opps:
                urgency_badge = "🔥 **URGENT**" if opp.is_urgent else ""
                score_color = "green" if opp.relevance_score >= 80 else ("orange" if opp.relevance_score >= 50 else "red")
                
                with st.expander(f"{opp.title} - Score: {opp.relevance_score} {urgency_badge}"):
                    st.write(f"**Source:** [{opp.source}]({opp.url}) | **Published:** {opp.published_date} | **Difficulty:** {opp.difficulty_level}")
                    st.markdown(f"**AI Reasoning:** _{opp.reasoning}_")
                    st.markdown("---")
                    st.write("**Description Preview:**")
                    st.text(opp.description.strip())
                    
                    # Draft Section
                    draft = database.get_draft(opp.id)
                    if draft:
                        st.markdown("### 📝 Auto-Generated Draft")
                        st.text_area("Ready to Send:", value=draft, height=200, key=f"draft_{opp.id}")
                        
                        if opp.status == 'applied':
                            st.success("✅ Application Approved and Sent!")
                        else:
                            if st.button("🚀 Approve & Auto-Apply", key=f"apply_{opp.id}"):
                                database.update_opportunity_status(opp.id, 'applied')
                                st.rerun()
                    else:
                        st.info("No draft generated. (Drafts are auto-generated for score > 80)")
                    
    with col2:
        st.subheader("📊 Stats")
        st.metric("Total Opportunites Tracked", len(opps))
        high_value = len([o for o in opps if o.relevance_score >= 80])
        st.metric("High-Value Matches (>80)", high_value)
        
        st.markdown("---")
        st.markdown("### 📧 Notifications")
        user_email = st.text_input("Enter your email address to receive summary directly:")
        if st.button("📨 Send Gmail Summary Now"):
            email_opps = [o for o in opps if o.status != 'applied']
            if email_opps:
                if not user_email or "@" not in user_email:
                    st.error("Please provide a valid email address.")
                else:
                    with st.spinner(f"Sending email out to {user_email}..."):
                        from notifier import send_email_summary
                        try:
                            send_email_summary(email_opps, receiver_email=user_email)
                            st.success(f"✅ Email sent successfully to {user_email}!")
                        except Exception as e:
                            st.error(f"❌ Could not send email: {str(e)}")
            else:
                st.warning("No unapplied opportunities to email.")
                
        st.markdown("---")
        st.markdown("### ⚙️ Engine Status")
        st.write("To continuously discover opportunities, run the background worker:")
        st.code("python scheduler.py", language="bash")
        
        if st.button("🔄 Re-Scan & Re-Evaluate Now"):
            with st.spinner("Scraping fresh opportunities..."):
                from scraper import run_all_scrapers
                raw_opps = run_all_scrapers()
                for opp in raw_opps:
                    database.save_opportunity(opp)
            status_ph2 = st.empty()
            with st.spinner("Re-evaluating all opportunities against your profile..."):
                re_evaluate_existing(profile, status_ph2)
            status_ph2.empty()
            st.success(f"✅ Scan complete! Found {len(raw_opps)} fresh opportunities and re-evaluated everything.")
            st.rerun()
