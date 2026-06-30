import csv
import time
import random
import os
import re
import logging
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from datetime import datetime
import undetected_chromedriver as uc
from utils import get_chromedriver_path, clean_persian_text

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- تنظیمات اصلی ---
CATEGORIES = [
    "https://jobvision.ir/jobs/category/developer",
    "https://jobvision.ir/jobs/category/data-science"
]
MAX_PAGES = 10
MAX_RETRIES = 3

# ساخت نام فایل با تاریخ امروز (مثال: jobs-2024-06-29.csv)
today_date = datetime.now().strftime("%Y-%m-%d")
CSV_FILE = f"jobs-{today_date}.csv"
def setup_driver():
    """راه‌اندازی مرورگر با فایل درایور لوکال (برای دور زدن تحریم دانلود)"""
    options = uc.ChromeOptions()
    
    # اجرای مرورگر در پس‌زمینه
    options.add_argument("--headless") 
    
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # جلوگیری از دانلود عکس‌ها برای سرعت بیشتر
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.page_load_strategy = 'eager'
    
    # معرفی مسیر درایور به کتابخانه (خودکار یا دستی)
    driver_path = get_chromedriver_path()
    try:
        if driver_path:
            driver = uc.Chrome(options=options, driver_executable_path=driver_path)
        else:
            driver = uc.Chrome(options=options)
    except Exception as e:
        logging.warning(f"ChromeDriver auto-detection failed ({e}), retrying without explicit path...")
        driver = uc.Chrome(options=options)
    
    return driver
# clean_persian_text is imported from utils.py

def is_recent_job(card_text):
    """بررسی تاریخ انتشار آگهی با پشتیبانی از زبان فارسی و انگلیسی"""
    if not card_text:
        return True
        
    # یکسان‌سازی حروف و اعداد
    text = card_text.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')).lower()
    
    # کلمات کلیدی برای آگهی‌های بسیار جدید
    if any(keyword in text for keyword in ["امروز", "دیروز", "ساعت", "دقیقه", "لحظه", "today", "yesterday", "hour", "minute", "just now"]):
        return True
        
    # بررسی روز (فارسی و انگلیسی)
    day_match = re.search(r'(\d+)\s*(?:روز\s*پیش|days?\s*ago)', text)
    if day_match:
        return int(day_match.group(1)) <= 7
        
    # بررسی هفته (فارسی و انگلیسی)
    week_match = re.search(r'(\d+)\s*(?:هفته\s*پیش|weeks?\s*ago)', text)
    if week_match:
        return int(week_match.group(1)) <= 1
        
    # ماه و سال قطعا بیشتر از یک هفته هستند
    if any(keyword in text for keyword in ["ماه پیش", "سال پیش", "month ago", "year ago", "months ago"]):
        return False
        
    return True

def safe_get(driver, url, wait_selector=None):
    """نسخه سریع‌تر از باز کردن لینک‌ها با حداقل تاخیر ضروری"""
    for attempt in range(MAX_RETRIES):
        try:
            # کاهش چشمگیر زمان توقف قبل از باز کردن لینک (۱ تا ۲.۵ ثانیه)
            time.sleep(random.uniform(1.0, 2.5))
            driver.get(url)
            
            if wait_selector:
                # صبر هوشمند: به محض پیدا شدن المان کار را ادامه بده
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )
            else:
                # توقف کوتاه فقط برای اطمینان از رندر شدن جاوااسکریپت Vue.js
                time.sleep(random.uniform(1.0, 1.5))
                
            return BeautifulSoup(driver.page_source, 'html.parser')
            
        except (TimeoutException, WebDriverException) as e:
            logging.warning(f"Attempt {attempt + 1} failed for {url}. Retrying...")
            time.sleep(3)
            
    logging.error(f"Failed to load {url} after {MAX_RETRIES} attempts.")
    return None

def extract_job_links(driver, category_url):
    """استخراج لینک‌های آگهی با فیلتر دقیق لینک‌های اضافی (دسته‌بندی/شهر/کلمات کلیدی)"""
    job_links = set()
    
    for page in range(1, MAX_PAGES + 1):
        logging.info(f"Scraping category {category_url} - Page {page}")
        page_url = f"{category_url}?page={page}"
        
        soup = safe_get(driver, page_url)
        if not soup:
            continue
            
        total_links_on_page = 0
        recent_links_found = 0
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # 🎯 فیلتر صحیح و منطقی:
            # لینک باید شامل /jobs/ باشد
            # اما به هیچ وجه نباید کلمات category (شهرها و دسته‌ها) و keyword (برچسب‌ها) را داشته باشد
            if '/jobs/' in href and '/category/' not in href and '/keyword/' not in href:
                total_links_on_page += 1
                
                parent = a_tag
                for _ in range(5):
                    if parent.parent:
                        parent = parent.parent
                        if any(t in parent.get_text().lower() for t in ["پیش", "امروز", "دیروز", "ago", "today", "yesterday"]):
                            break
                
                card_text = parent.get_text()
                
                if is_recent_job(card_text):
                    full_url = f"https://jobvision.ir{href}" if not href.startswith('http') else href
                    job_links.add(full_url)
                    recent_links_found += 1
                
        logging.info(f"Found {recent_links_found} RECENT jobs out of {total_links_on_page} on page {page}.")
        
        if total_links_on_page > 0 and recent_links_found == 0:
            logging.info("All jobs on this page are older than 1 week. Stopping pagination.")
            break
            
        if total_links_on_page == 0:
            logging.info("No jobs found on page. Ending pagination.")
            break
            
    return list(job_links)

def extract_job_details(driver, job_url):
    """استخراج اطلاعات با پشتیبانی همزمان از قالب‌های فارسی و انگلیسی"""
    soup = safe_get(driver, job_url)
    if not soup:
        return None

    try:
        title = "N/A"
        title_element = soup.find('h1')
        if title_element:
            title = clean_persian_text(title_element.get_text())

        city = "N/A"
        city_element = soup.find('span', class_=re.compile(r'yn_category'))
        
        if not city_element:
            city_element = soup.find(lambda tag: tag.name == "span" and any(k in tag.text for k in ["استخدام در", "Hiring in"]))
            
        if city_element:
            city_text = city_element.get_text()
            for w in ["استخدام در", "Hiring in"]:
                city_text = city_text.replace(w, "")
            city_text = re.sub(r'\s*،\s*', '، ', city_text)
            city_text = re.sub(r'\s*,\s*', ', ', city_text)
            city = clean_persian_text(city_text)
        else:
            header_details = soup.find_all('div', class_=re.compile(r'text-black'))
            for detail in header_details:
                text = detail.get_text()
                if any(keyword in text.lower() for keyword in ["تهران", "استان", "شهر ", "tehran", "province", "city"]):
                    city = clean_persian_text(text)
                    break

        description = "N/A"
        # اضافه شدن کلمات کلیدی انگلیسی
        desc_header = soup.find(lambda tag: tag.name in ["h2", "h3", "h4"] and 
                                any(k in tag.text.lower() for k in ["شرح شغل", "وظایف", "job description", "responsibilities", "requirements", "about the role"]))
        if desc_header:
            content_div = desc_header.find_next_sibling('div')
            if content_div:
                for br in content_div.find_all("br"):
                    br.replace_with(" | ") 
                description = clean_persian_text(content_div.get_text())
            else:
                 description = clean_persian_text(desc_header.parent.get_text(separator=" | "))
        else:
            fallback_container = soup.find('div', class_=re.compile(r'description|details|req', re.I))
            if fallback_container:
                 description = clean_persian_text(fallback_container.get_text(separator=" | "))

        # پاک‌سازی کلمات اضافی از اول توضیحات
        for w in ["شرح شغل و وظایف | ", "شرح شغل | ", "Job Description | ", "Responsibilities | ", "Requirements | "]:
            description = description.replace(w, "")
        description = description.strip()

        key_indicators = "N/A"
        # کلمات کلیدی انگلیسی برای شاخص‌ها
        key_header = soup.find(lambda tag: tag.name in ["h2", "h3", "h4"] and 
                               any(k in tag.text.lower() for k in ["شاخص های کلیدی", "key indicators", "key requirements"]))
        
        if key_header:
            header_parent = key_header.parent
            if header_parent:
                content_container = header_parent.find_next_sibling('div')
                if content_container:
                    texts = [clean_persian_text(text) for text in content_container.stripped_strings]
                    texts = [t for t in texts if t]
                    key_indicators = " | ".join(texts)

        return {
            'title': title,
            'city': city,
            'description_and_responsibilities': description,
            'key_indicators': key_indicators,
            'url': job_url
        }
    except Exception as e:
        logging.error(f"Error parsing job details for {job_url}: {e}")
        return None
    
def init_csv():
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
        # فیلد key_indicators به هدرها اضافه شد
        writer = csv.DictWriter(f, fieldnames=['title', 'city', 'description_and_responsibilities', 'key_indicators', 'url'])
        if not file_exists:
            writer.writeheader()
def save_job_incrementally(job_data):
    if not job_data:
        return
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
        # فیلد key_indicators باید حتماً اینجا هم باشد
        writer = csv.DictWriter(f, fieldnames=['title', 'city', 'description_and_responsibilities', 'key_indicators', 'url'])
        writer.writerow(job_data)
def main():
    driver = None
    all_job_links = set()
    processed_urls = set()
    
    stats = {
        'total_found': 0,
        'successful': 0,
        'failed': 0
    }
    
    if os.path.isfile(CSV_FILE):
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed_urls.add(row['url'])
                
    init_csv()

    try:
        logging.info("Starting Selenium WebDriver...")
        driver = setup_driver()

        for category in CATEGORIES:
            links = extract_job_links(driver, category)
            all_job_links.update(links)
            
        stats['total_found'] = len(all_job_links)
        logging.info(f"Total unique recent jobs found: {stats['total_found']}")

        for idx, url in enumerate(all_job_links, 1):
            if url in processed_urls:
                logging.info(f"[{idx}/{stats['total_found']}] Skipping already processed job: {url}")
                continue
                
            logging.info(f"[{idx}/{stats['total_found']}] Processing: {url}")
            job_data = extract_job_details(driver, url)
            
            # 🎯 فیلتر جدید: فقط آگهی‌هایی ذخیره شوند که عنوان دارند و شاخص کلیدی آن‌ها N/A نیست
            if job_data and job_data['title'] != "N/A" and job_data.get('key_indicators') != "N/A":
                save_job_incrementally(job_data)
                processed_urls.add(url)
                stats['successful'] += 1
            else:
                logging.info(f"[{idx}/{stats['total_found']}] Skipped (Missing Key Indicators): {url}")
                stats['failed'] += 1

    except KeyboardInterrupt:
        logging.warning("\nScript interrupted by user. Saving progress and exiting...")
    finally:
        if driver:
            driver.quit()
            
        print("\n" + "="*40)
        print("          SCRAPING SUMMARY")
        print("="*40)
        print(f"Total Recent Job Links Found: {stats['total_found']}")
        print(f"Successfully Extracted:       {stats['successful']}")
        print(f"Failed Extractions:           {stats['failed']}")
        print(f"Duplicates Skipped:           {len(processed_urls) - stats['successful']}")
        print("="*40)
        print(f"Data saved to {CSV_FILE}")

if __name__ == "__main__":
    main()