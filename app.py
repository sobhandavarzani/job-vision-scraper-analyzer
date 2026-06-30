import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import time
import random
import re
from datetime import datetime
import os
import io
import json
from utils import (
    get_chromedriver_path, KEYWORDS_POOL, clean_persian_text,
    extract_experience, extract_job_details as _extract_job_details,
)

# ==========================================
# History System Setup
# ==========================================
HISTORY_DIR = "history"
HISTORY_FILES_DIR = os.path.join(HISTORY_DIR, "files")
HISTORY_LOG_FILE = os.path.join(HISTORY_DIR, "history_log.json")

def init_history():
    if not os.path.exists(HISTORY_FILES_DIR):
        os.makedirs(HISTORY_FILES_DIR)
    if not os.path.exists(HISTORY_LOG_FILE):
        with open(HISTORY_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def load_history():
    if not os.path.exists(HISTORY_LOG_FILE):
        return []
    try:
        with open(HISTORY_LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, IOError):
        return []

def save_to_history(run_data, excel_buffer, img_buffer):
    init_history()
    history = load_history()
    history.append(run_data)
    
    # Save log file
    try:
        with open(HISTORY_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Error saving history log file: {e}")
        return

    # Save Excel file physically
    try:
        with open(run_data["excel_path"], "wb") as f:
            f.write(excel_buffer.getbuffer())
    except Exception as e:
        st.error(f"Error saving Excel file physically: {e}")

    # Save Image physically
    try:
        with open(run_data["image_path"], "wb") as f:
            f.write(img_buffer.getbuffer())
    except Exception as e:
        st.error(f"Error saving image physically: {e}")

# ==========================================
# Settings & Globals
# ==========================================

CATEGORIES_POOL = {
    "توسعه‌دهنده (Developer)": "https://jobvision.ir/jobs/category/developer",
    "علوم داده (Data Science)": "https://jobvision.ir/jobs/category/data-science",
    "دیجیتال مارکتینگ (Digital Marketing)": "https://jobvision.ir/jobs/category/digital-marketing",
    "تولید محتوا (Content)": "https://jobvision.ir/jobs/category/content",
    "تست نرم‌افزار (Software QA)": "https://jobvision.ir/jobs/category/software-qa",
    "شبکه و زیرساخت (Network)": "https://jobvision.ir/jobs/category/network",
    "بازی‌سازی (Game Development)": "https://jobvision.ir/jobs/category/game",
    "طراحی گرافیک (Graphics)": "https://jobvision.ir/jobs/category/graphics",
    "طراحی UI/UX": "https://jobvision.ir/jobs/category/ui-ux",
    "مدیریت محصول (Product Manager)": "https://jobvision.ir/jobs/category/product-manager",
    "توسعه کسب‌وکار (Business Development)": "https://jobvision.ir/jobs/category/business-development",
    "معامله‌گر / تریدر (Trader)": "https://jobvision.ir/jobs/category/trader"
}

# KEYWORDS_POOL is imported from utils.py

MAX_PAGES = 40 
MAX_RETRIES = 3

# ==========================================
# Scraper & Analyzer Logic
# ==========================================

def setup_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless") 
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.page_load_strategy = 'eager'
    
    driver_path = get_chromedriver_path()
    try:
        if driver_path:
            driver = uc.Chrome(options=options, driver_executable_path=driver_path)
        else:
            driver = uc.Chrome(options=options)
    except Exception as e:
        st.warning(f"ChromeDriver auto-detection failed ({e}), retrying without explicit path...")
        driver = uc.Chrome(options=options)
    return driver

def safe_get_page(driver, url):
    """Navigate to URL and return parsed BeautifulSoup, with retries."""
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(random.uniform(2.0, 3.5))
            driver.get(url)
            time.sleep(3.0)
            return BeautifulSoup(driver.page_source, 'html.parser')
        except (WebDriverException, TimeoutException) as e:
            st.warning(f"Attempt {attempt+1}/{MAX_RETRIES} failed for {url}: {e}")
            time.sleep(2)
    return None

def scrape_job_details(driver, job_url):
    """Scrape a single job posting page and extract structured data."""
    soup = safe_get_page(driver, job_url)
    if not soup:
        return None
    try:
        title_element = soup.find('h1')
        title = clean_persian_text(title_element.get_text()) if title_element else "N/A"
        city = "N/A"
        city_element = soup.find('span', class_=re.compile(r'yn_category'))
        if not city_element:
            city_element = soup.find(lambda tag: tag.name == "span" and any(k in tag.text for k in ["استخدام در", "Hiring in"]))
        if city_element:
            city_text = city_element.get_text().replace("استخدام در", "").replace("Hiring in", "")
            city = clean_persian_text(re.sub(r'\s*[،,]\s*', '، ', city_text))
        description = "N/A"
        desc_header = soup.find(lambda tag: tag.name in ["h2", "h3", "h4"] and any(k in tag.text.lower() for k in ["شرح شغل", "وظایف", "job description"]))
        if desc_header:
            content_div = desc_header.find_next_sibling('div')
            if content_div:
                for br in content_div.find_all("br"):
                    br.replace_with(" | ") 
                description = clean_persian_text(content_div.get_text())
        key_indicators = "N/A"
        key_header = soup.find(lambda tag: tag.name in ["h2", "h3", "h4"] and any(k in tag.text.lower() for k in ["شاخص های کلیدی", "key indicators"]))
        if key_header and key_header.parent:
            content_container = key_header.parent.find_next_sibling('div')
            if content_container:
                texts = [clean_persian_text(text) for text in content_container.stripped_strings if text]
                key_indicators = " | ".join(texts)
        return {'title': title, 'city': city, 'description_and_responsibilities': description, 'key_indicators': key_indicators, 'url': job_url}
    except Exception as e:
        st.warning(f"Error extracting job details from {job_url}: {e}")
        return None

def analyze_data(df, selected_skills=None):
    text_cols = ['title', 'description_and_responsibilities', 'key_indicators']
    df['combined_text'] = df[text_cols].fillna('').astype(str).agg(' '.join, axis=1)
    df['combined_text_lower'] = df['combined_text'].str.lower()
    
    if selected_skills:
        pattern_list = [KEYWORDS_POOL[skill] for skill in selected_skills]
        combined_pattern = "|".join(pattern_list)
        df = df[df['combined_text_lower'].str.contains(combined_pattern, regex=True)]
    
    total_jobs = len(df)
    if total_jobs == 0:
        return None, None, None, 0, df
    
    skills_to_check = selected_skills if selected_skills else KEYWORDS_POOL.keys()
    skills_results = {}
    for skill in skills_to_check:
        pattern = KEYWORDS_POOL[skill]
        skills_results[skill] = df['combined_text_lower'].apply(lambda x: bool(re.search(pattern, x))).sum()
        
    remote_count = df['combined_text_lower'].apply(lambda x: bool(re.search(r'دورکاری|ریموت|remote|دورکار', x))).sum()
    hybrid_count = df['combined_text_lower'].apply(lambda x: bool(re.search(r'هیبرید|hybrid|نیمه‌حضوری', x))).sum()
    onsite_count = total_jobs - (remote_count + hybrid_count)
    
    df['extracted_exp'] = df['combined_text_lower'].apply(extract_experience)
    avg_exp = df['extracted_exp'].mean()
    
    modes = {"Remote": remote_count, "Hybrid": hybrid_count, "Onsite/Other": onsite_count}
    return skills_results, modes, avg_exp, total_jobs, df

# ==========================================
# Streamlit UI Initialization
# ==========================================
st.set_page_config(page_title="Smart Job Market Dashboard", layout="wide", page_icon="📊")

init_history() 

if 'scraped_data' not in st.session_state:
    st.session_state['scraped_data'] = None
if 'is_new_run' not in st.session_state:
    st.session_state['is_new_run'] = False
if 'selected_history_run' not in st.session_state:
    st.session_state['selected_history_run'] = None

st.title("📊 Integrated Job Posting Scraper & Analyzer")
st.markdown("This system scrapes JobVision postings in real-time and analyzes them using AI.")

# --- Improved Sidebar Layout ---
st.sidebar.header("⚙️ Settings & Filters Panel")

with st.sidebar.container():
    st.markdown("### 📂 Categories")
    selected_category_names = st.multiselect(
        "Select Job Category (Required):",
        options=list(CATEGORIES_POOL.keys()),
        default=["توسعه‌دهنده (Developer)"]
    )

st.sidebar.markdown("---")

with st.sidebar.container():
    st.markdown("### 📅 Timeframe")
    
    time_options = {
        "3 Days": "&searchTimeRange=1",
        "1 Week": "&searchTimeRange=2",
        "15 Days": "&searchTimeRange=3",
        "1 Month": "&searchTimeRange=4",
        "All Ads": "" 
    }
    selected_time_name = st.radio(
        "Select Job Posting Timeframe:",
        options=list(time_options.keys()),
        index=1 
    )
    time_param = time_options[selected_time_name]

st.sidebar.markdown("---")

with st.sidebar.container():
    st.markdown("### 🛠️ Skills")
    selected_skills = st.multiselect(
        "Filter by Specific Skills (Optional):",
        options=list(KEYWORDS_POOL.keys()),
        help="If left empty, all ads will be extracted."
    )

st.sidebar.markdown("---")
start_btn = st.sidebar.button("🚀 Start Scraping & Analysis", use_container_width=True, type="primary")

# --- History Panel in Sidebar ---
st.sidebar.markdown("---")
st.sidebar.header("🗂️ Run History")
history_records = load_history()

if not history_records:
    st.sidebar.info("No history found.")
else:
    for i, run in enumerate(history_records):
        cat_clean = run.get('categories', 'Unknown').replace('(', '').replace(')', '')
        expander_title = f"{cat_clean} - {run.get('timeframe', 'Unknown')}"
        
        with st.sidebar.expander(expander_title):
            st.caption(f"🕒 Scrape Time: {run.get('timestamp')}")
            st.caption(f"📊 Total Ads: {run.get('total_ads')}")
            
            if st.button("👁️ View in Main Panel", key=f"btn_hist_{i}_{run.get('id', i)}"):
                st.session_state['selected_history_run'] = run
                st.rerun() 

# --- App Logic ---
if start_btn:
    st.session_state['selected_history_run'] = None
    
    if not selected_category_names:
        st.error("Error: Please select at least one job category.")
    else:
        scraped_data = []
        progress_text = st.empty()
        
        with st.spinner('Initializing the scraper bot (Please wait)...'):
            driver = setup_driver()
            try:
                all_job_links = set()
                for cat_name in selected_category_names:
                    cat_url = CATEGORIES_POOL[cat_name]
                    progress_text.info(f"Searching in category: {cat_name} ...")
                    
                    for page in range(1, MAX_PAGES + 1):
                        page_url = f"{cat_url}?page={page}&sort=1{time_param}"
                        soup = safe_get_page(driver, page_url)
                        if not soup: break
                        
                        total_links_on_page = 0
                        
                        for a_tag in soup.find_all('a', href=True):
                            href = a_tag['href']
                            if '/jobs/' in href and '/category/' not in href and '/keyword/' not in href:
                                total_links_on_page += 1
                                full_url = f"https://jobvision.ir{href}" if not href.startswith('http') else href
                                all_job_links.add(full_url)
                                
                        if total_links_on_page == 0:
                            break 
                
                total_links = len(all_job_links)
                if total_links == 0:
                    st.warning("No new jobs found in these categories for the selected timeframe.")
                else:
                    progress_bar = st.progress(0)
                    for idx, url in enumerate(all_job_links):
                        progress_text.text(f"Extracting job {idx+1} of {total_links}...")
                        job_data = scrape_job_details(driver, url)
                        if job_data and job_data['title'] != "N/A":
                            scraped_data.append(job_data)
                        progress_bar.progress((idx + 1) / total_links)
                    
                    progress_text.success(f"Scraping completed successfully. Found {len(scraped_data)} valid jobs.")
                    st.session_state['scraped_data'] = scraped_data
                    st.session_state['is_new_run'] = True 
            finally:
                driver.quit()

# ==========================================
# Main Dashboard Rendering
# ==========================================

if st.session_state.get('selected_history_run'):
    run = st.session_state['selected_history_run']
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader(f"🕰️ History View: {run.get('categories', '')} - {run.get('timeframe', '')}")
    with col2:
        if st.button("❌ Close History", use_container_width=True):
            st.session_state['selected_history_run'] = None
            st.rerun()
            
    st.markdown(f"**Scraped at:** {run.get('timestamp')} | **Total Ads:** {run.get('total_ads')}")
    st.markdown("---")
    
    col_chart, col_data = st.columns([2, 1])
    with col_chart:
        st.write("**Skills Demand Chart**")
        if os.path.exists(run.get('image_path', '')):
            st.image(run['image_path'], use_container_width=True)
        else:
            st.warning("Chart image not found.")
            
    with col_data:
        if 'modes_data' in run:
            st.write("**Collaboration Type Details**")
            st.dataframe(pd.DataFrame(run['modes_data'], columns=["Type", "Count"]), use_container_width=True)
            
        if 'raw_preview' in run:
            st.write("**Extracted Data (Sample)**")
            st.dataframe(pd.DataFrame(run['raw_preview']), use_container_width=True)

elif st.session_state.get('scraped_data'):
    df = pd.DataFrame(st.session_state['scraped_data'])
    
    with st.spinner('Processing and analyzing data...'):
        skills_res, modes_res, avg_exp, total_ads, filtered_df = analyze_data(df, selected_skills)
    
    eng_cats = [re.search(r'\((.*?)\)', cat).group(1).strip() if re.search(r'\((.*?)\)', cat) else cat for cat in selected_category_names]
    cats_str = "(" + " - ".join(eng_cats) + ")"
    cats_str = re.sub(r'[\\/*?:"<>|]', '_', cats_str)
    
    time_abbr_map = {"3 Days": "3D", "1 Week": "1W", "15 Days": "15D", "1 Month": "1M", "All Ads": "ALL"}
    time_str = time_abbr_map.get(selected_time_name, "Unknown")
    
    skills_str = "_".join([re.sub(r'[\\/*?:"<>|]', '', s).strip() for s in selected_skills])[:80] if selected_skills else "AllSkills"
    date_str = datetime.now().strftime('%Y-%m-%d')
    dynamic_filename_base = f"{cats_str}_{time_str}_{skills_str}_{date_str}"
    
    run_id = datetime.now().strftime("%H%M%S")
    
    if total_ads == 0:
        st.warning("The found job postings did not contain your selected skills.")
    else:
        st.markdown("---")
        st.subheader(f"📈 Job Market Analysis Results (Matched Ads: {total_ads})")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Analyzed Ads", total_ads)
        col2.metric("Avg Required Experience", f"{avg_exp:.1f} years" if pd.notnull(avg_exp) else "Unknown")
        col3.metric("Remote Positions", modes_res.get("Remote", 0))
        col4.metric("Hybrid Positions", modes_res.get("Hybrid", 0))

        st.markdown("---")
        col_chart, col_data = st.columns([2, 1])

        # Generate photos for automatic saving
        img_buffer = io.BytesIO()
        with col_chart:
            st.write("**Skills Demand Chart**")
            skills_df = pd.DataFrame(list(skills_res.items()), columns=['Skill', 'Count']).sort_values(by='Count', ascending=False)
            skills_df = skills_df[skills_df['Count'] > 0] 
            skills_df['Percentage'] = (skills_df['Count'] / total_ads) * 100
            
            if not skills_df.empty:
                fig, ax = plt.subplots(figsize=(10, 6))
                sns.barplot(x="Percentage", y="Skill", data=skills_df, palette="plasma", ax=ax)
                ax.set_xlabel("Percentage of Ads (%)")
                ax.set_ylabel("Technology / Skill")
                for p in ax.patches:
                    width = p.get_width()
                    ax.text(width + 0.5, p.get_y() + p.get_height()/2 + 0.1, f'{width:.1f}%', ha="left", va="center", fontsize=9)
                
                st.pyplot(fig)
                fig.savefig(img_buffer, format="png", bbox_inches="tight", dpi=300)
                img_buffer.seek(0)
            else:
                st.info("None of the listed skills were found in these ads.")

        # Generate Excel for auto-saving
        excel_buffer = io.BytesIO()
        with col_data:
            st.write("**Collaboration Type Details**")
            modes_df = pd.DataFrame(list(modes_res.items()), columns=["Collaboration Type", "Count"])
            st.dataframe(modes_df, use_container_width=True)
            
            st.write("**Extracted Data (Raw)**")
            st.dataframe(filtered_df[['title', 'city', 'url']].head(10), use_container_width=True)

            export_df = filtered_df.drop(columns=['combined_text', 'combined_text_lower', 'extracted_exp'], errors='ignore')
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                export_df.to_excel(writer, sheet_name="Scraped Jobs", index=False)
                modes_df.to_excel(writer, sheet_name="Collaboration Modes", index=False)
            excel_buffer.seek(0)
            
        # Auto-save to history and display message
        if st.session_state['is_new_run']:
            excel_filename = f"{dynamic_filename_base}_{run_id}.xlsx"
            image_filename = f"{dynamic_filename_base}_{run_id}.png"
            
            excel_absolute_path = os.path.join(HISTORY_FILES_DIR, excel_filename)
            image_absolute_path = os.path.join(HISTORY_FILES_DIR, image_filename)

            run_metadata = {
                "id": f"{date_str}_{run_id}",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "categories": cats_str,
                "timeframe": selected_time_name, 
                "skills_filter": skills_str,
                "total_ads": int(total_ads),  
                "excel_path": excel_absolute_path,
                "image_path": image_absolute_path,
                "modes_data": [(k, int(v)) for k, v in modes_res.items()],
                "raw_preview": filtered_df[['title', 'city', 'url']].head(10).fillna("N/A").to_dict('records')
            }
            
            save_to_history(run_metadata, excel_buffer, img_buffer)
            st.session_state['is_new_run'] = False
            
            st.success(f"✅ Scraping finished successfully! Results have been automatically saved to: `{HISTORY_FILES_DIR}`")