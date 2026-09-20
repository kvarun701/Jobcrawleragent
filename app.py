import streamlit as st
import asyncio
import pandas as pd
import sys
import os
import re
import subprocess
import importlib
import scraper
importlib.reload(scraper)
from scraper import run_scraper

# Ensure Playwright chromium binaries are located properly
def ensure_playwright():
    possible_paths = [
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH"),
        "/Users/varun/Library/Caches/ms-playwright",
        os.path.expanduser("~/Library/Caches/ms-playwright"),
        os.path.expanduser("~/.cache/ms-playwright")
    ]
    for p in possible_paths:
        if p and os.path.exists(p) and os.listdir(p):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = p
            return
            
    try:
        subprocess.run(["playwright", "install", "chromium"], check=False)
    except Exception:
        pass

ensure_playwright()

# Configure the page
st.set_page_config(
    page_title="CrawlJobs - Search Latest 24-Hour Jobs from LinkedIn, Indeed, Naukri, Instahyre & Cutshort",
    page_icon="💼",
    layout="wide"
)

# SEO and OpenGraph Meta Tags for Social Sharing & Search Engines
st.markdown("""
<head>
    <meta name="description" content="Search fresh jobs posted in the past 24 hours across LinkedIn, Indeed, Naukri, Instahyre, Cutshort, and Remote OK. Free multi-platform job crawler." />
    <meta name="keywords" content="jobs, job search, linkedin jobs, indeed jobs, naukri jobs, instahyre jobs, cutshort jobs, 24 hours jobs, software engineer jobs, remote jobs" />
    <meta property="og:title" content="CrawlJobs — One Portal for Latest 24-Hour Jobs" />
    <meta property="og:description" content="Stop searching 10 tabs. Find freshly posted jobs from LinkedIn, Indeed, Naukri, Instahyre, Cutshort & Remote OK in one unified dashboard." />
    <meta property="og:url" content="https://crawljobs.online/" />
    <meta property="og:type" content="website" />
</head>
""", unsafe_allow_html=True)

st.title("💼 CrawlJobs — Multi-Portal Job Crawler")
st.markdown("Search for the latest verified job listings posted in the **past 24 hours** across **LinkedIn**, **Indeed**, **Naukri**, **Instahyre**, **Cutshort**, and **Remote OK**.")

# User inputs
col1, col2, col3, col4 = st.columns([2, 1.8, 1.3, 1.4])
with col1:
    keyword = st.text_input("Job Title / Keyword", placeholder="e.g. Software Engineer, Android, Python").strip()
with col2:
    location = st.text_input("Location", placeholder="e.g. India, Noida, Bengaluru, Remote").strip()
with col3:
    exp_options = ["Any Experience"] + [f"{i} Year{'s' if i != 1 else ''}{' (Fresher)' if i == 0 else ''}" for i in range(0, 46)]
    selected_exp = st.selectbox(
        "Experience",
        exp_options,
        index=0,
        help="Filter jobs by required experience up to 45 years"
    )
    experience_val = None if selected_exp == "Any Experience" else int(selected_exp.split()[0])
with col4:
    region = st.selectbox(
        "Indeed Market",
        ["India (in.indeed.com)", "Global / US (indeed.com)", "Auto-detect"],
        index=0,
        help="Select whether to search Indian Indeed (in.indeed.com) or Global/US Indeed (indeed.com)"
    )

search_clicked = st.button("Search Latest Jobs (Past 24 Hours)", type="primary", use_container_width=True)

# Preserve search results across Streamlit interactions/downloads using session state
if "jobs_data" not in st.session_state:
    st.session_state["jobs_data"] = None
if "search_query" not in st.session_state:
    st.session_state["search_query"] = {"keyword": "", "location": "", "region": "", "experience": "Any Experience"}

if search_clicked:
    if not keyword or not location:
        st.warning("Please enter both a job keyword and a location.")
    else:
        exp_info = f", Experience: {selected_exp}" if experience_val is not None else ""
        with st.spinner(f"Crawling past 24 hours jobs concurrently for '{keyword}' in '{location}' ({region}{exp_info})..."):
            try:
                # Windows specific asyncio fix if needed
                if sys.platform == 'win32':
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                
                # Run the multi-platform scraper
                jobs = asyncio.run(run_scraper(keyword, location, region=region, experience=experience_val))
                st.session_state["jobs_data"] = jobs
                st.session_state["search_query"] = {
                    "keyword": keyword,
                    "location": location,
                    "region": region,
                    "experience": selected_exp
                }
                
            except Exception as e:
                st.error(f"An error occurred while crawling jobs: {str(e)}")

# Display results if available
if st.session_state["jobs_data"] is not None:
    jobs = st.session_state["jobs_data"]
    q_keyword = st.session_state["search_query"]["keyword"]
    q_location = st.session_state["search_query"]["location"]
    q_exp = st.session_state["search_query"].get("experience", "Any Experience")
    exp_suffix = f" ({q_exp})" if q_exp != "Any Experience" else ""
    
    if jobs:
        df = pd.DataFrame(jobs)

        # Helper to parse posted date string into numeric age in hours for accurate sorting
        def parse_posted_age_hours(val):
            if not val or not isinstance(val, str):
                return 9999.0
            val_clean = val.lower().strip()
            
            if any(w in val_clean for w in ["just now", "few moments", "moments ago"]):
                return 0.1
            if any(w in val_clean for w in ["few hours ago", "today"]):
                return 4.0
            if "past 24 hours" in val_clean or "yesterday" in val_clean:
                return 24.0
                
            m_min = re.search(r"(\d+)\s*(?:minute|min|m\b)", val_clean)
            if m_min:
                return float(m_min.group(1)) / 60.0
                
            m_hr = re.search(r"(\d+)\s*(?:hour|hr|h\b)", val_clean)
            if m_hr:
                return float(m_hr.group(1))
                
            m_day = re.search(r"(\d+)\s*(?:day|d\b)", val_clean)
            if m_day:
                return float(m_day.group(1)) * 24.0
                
            m_wk = re.search(r"(\d+)\s*(?:week|w\b)", val_clean)
            if m_wk:
                return float(m_wk.group(1)) * 24.0 * 7.0
                
            m_mo = re.search(r"(\d+)\s*(?:month|mo\b)", val_clean)
            if m_mo:
                return float(m_mo.group(1)) * 24.0 * 30.0
                
            return 999.0

        # Sort posted date in ascending order (Newest/Freshest first)
        if "Posted" in df.columns:
            df["_age_hours"] = df["Posted"].apply(parse_posted_age_hours)
            df = df.sort_values(by="_age_hours", ascending=True).reset_index(drop=True)
            df = df.drop(columns=["_age_hours"])

        # Ensure optimal column order including Experience
        cols = [c for c in ["Platform", "Title", "Company", "Location", "Experience", "Posted", "Link"] if c in df.columns]
        other_cols = [c for c in df.columns if c not in cols]
        df = df[cols + other_cols]
        
        st.success(f"Successfully found {len(df)} jobs posted in the past 24 hours for '{q_keyword}' in '{q_location}'{exp_suffix}!")
        st.caption(f"🕒 Listings sorted by **Posted Date (Ascending / Newest first)** and filtered for **{q_exp}**.")
        
        # Primary platforms expected by the user
        primary_platforms = ["LinkedIn", "Indeed", "Naukri", "Instahyre", "Cutshort", "Remote OK"]
        
        # Collect any additional platforms returned by the crawler (e.g., ZipRecruiter)
        scraped_platforms = list(df["Platform"].unique())
        other_platforms = [p for p in scraped_platforms if p not in primary_platforms]
        all_platforms = primary_platforms + other_platforms
        
        # Display platform metric summaries in columns
        metric_cols = st.columns(1 + len(all_platforms))
        metric_cols[0].metric("All Jobs (24h)", len(df))
        
        for idx, platform in enumerate(all_platforms):
            count = int((df["Platform"] == platform).sum())
            metric_cols[idx + 1].metric(platform, count)
            
        st.markdown("---")
        
        # Build tab titles with counts
        tab_titles = [f"All jobs ({len(df)})"]
        for platform in all_platforms:
            count = int((df["Platform"] == platform).sum())
            tab_titles.append(f"{platform} ({count})")
            
        tabs = st.tabs(tab_titles)
        
        col_cfg = {
            "Link": st.column_config.LinkColumn("Apply Link"),
            "Experience": st.column_config.TextColumn("Experience"),
            "Posted": st.column_config.TextColumn("Posted Date")
        }
        
        # Tab 1: All Jobs
        with tabs[0]:
            st.dataframe(
                df,
                column_config=col_cfg,
                hide_index=True,
                use_container_width=True
            )
            csv_all = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download All Results (CSV)",
                data=csv_all,
                file_name=f'all_jobs_24h_{q_keyword.replace(" ", "_")}.csv',
                mime='text/csv',
                key="download_all_csv"
            )
            
        # Tab 2+: Individual Platform Tabs (LinkedIn, Indeed, Remote OK, etc.)
        for tab_idx, platform in enumerate(all_platforms, start=1):
            with tabs[tab_idx]:
                platform_df = df[df["Platform"] == platform]
                if not platform_df.empty:
                    st.dataframe(
                        platform_df,
                        column_config=col_cfg,
                        hide_index=True,
                        use_container_width=True
                    )
                    csv_platform = platform_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label=f"📥 Download {platform} CSV",
                        data=csv_platform,
                        file_name=f'{platform.lower().replace(" ", "_")}_jobs_24h.csv',
                        mime='text/csv',
                        key=f"download_{platform.lower().replace(' ', '_')}_csv"
                    )
                else:
                    st.info(f"No listings found on {platform} in the past 24 hours for '{q_keyword}' in '{q_location}'.")
                    if platform == "Indeed":
                        st.caption("Tip: Indeed may occasionally prompt for a bot check. Try searching with a broader location or specific title.")
                    elif platform == "Naukri":
                        st.caption("Tip: Naukri is India's leading job portal. Try searching by city (e.g. Noida, Bengaluru, Pune, Delhi).")
                    elif platform == "Instahyre":
                        st.caption("Tip: Instahyre focuses on curated tech, engineering, and startup roles across India.")
                    elif platform == "Cutshort":
                        st.caption("Tip: Cutshort connects fast-growing tech teams and startups with developers.")
                    elif platform == "Remote OK":
                        st.caption("Tip: Remote OK specializes in remote tech listings. Try searching tags like developer, engineer, python, or react.")
                        
    else:
        st.warning("No jobs were found matching your criteria. Platforms might have temporarily blocked requests with CAPTCHAs or no jobs match.")
