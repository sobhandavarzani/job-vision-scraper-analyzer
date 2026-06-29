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

# اضافه کردن کتابخانه جدید
import undetected_chromedriver as uc

# تنظیمات لاگ برای نمایش وضعیت اسکریپت
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- تنظیمات اصلی ---
CATEGORIES = [
    "https://jobvision.ir/jobs/category/developer",
    "https://jobvision.ir/jobs/category/data-science"
]
MAX_PAGES = 10
CSV_FILE = "jobs.csv"
MAX_RETRIES = 3

def setup_driver():
    """راه‌اندازی مرورگر با استفاده از undetected_chromedriver برای دور زدن فایروال و تحریم‌ها"""
    
    # ۱. ابتدا باید متغیر options تعریف شود
    options = uc.ChromeOptions()
    
    # ۲. سپس تنظیمات را به آن اضافه می‌کنیم
    # برای دیدن مرورگر، می‌توانید این خط را کامنت کنید (پیشنهاد می‌کنم بار اول کامنت کنید تا با چشم ببینید)
    # options.add_argument("--headless") 
    
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # ۳. در نهایت، درایور را فقط یک بار و با تعیین نسخه ۱۴۹ اجرا می‌کنیم
    driver = uc.Chrome(options=options, version_main=149)
    
    return driver
def clean_persian_text(text):
    """پاک‌سازی فاصله‌های اضافی و استانداردسازی متن‌های فارسی"""
    if not text:
        return ""
    cleaned = re.sub(r'\s+', ' ', text)
    return cleaned.strip()
def is_recent_job(card_text):
    """بررسی می‌کند که آیا زمان انتشار آگهی در محدوده ۷ روز گذشته است یا خیر"""
    if not card_text:
        return True
        
    # تبدیل اعداد فارسی به انگلیسی برای محاسبه ریاضی
    text = card_text.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789'))
    
    # کلماتی که قطعا مال همین اواخر هستند
    if any(keyword in text for keyword in ["امروز", "دیروز", "ساعت", "دقیقه", "لحظه"]):
        return True
        
    # استخراج روز
    day_match = re.search(r'(\d+)\s*روز\s*پیش', text)
    if day_match:
        return int(day_match.group(1)) <= 7
        
    # استخراج هفته (۱ هفته پیش قبول است، ۲ هفته پیش رد می‌شود)
    week_match = re.search(r'(\d+)\s*هفته\s*پیش', text)
    if week_match:
        return int(week_match.group(1)) <= 1
        
    # ماه و سال قطعا بیشتر از یک هفته هستند
    if "ماه پیش" in text or "سال پیش" in text:
        return False
        
    # اگر زمان پیدا نشد (برای جلوگیری از حذف اشتباه دیتا)، آن را مجاز می‌کنیم
    return True
def safe_get(driver, url, wait_selector=None):
    """باز کردن لینک با قابلیت تلاش مجدد (Retry) و تاخیر تصادفی"""
    for attempt in range(MAX_RETRIES):
        try:
            # تاخیر تصادفی بین ۳ تا ۷ ثانیه برای شبیه‌سازی رفتار انسان
            time.sleep(random.uniform(3.0, 7.0))
            driver.get(url)
            
            if wait_selector:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )
            else:
                time.sleep(random.uniform(2.0, 4.0))
                
            return BeautifulSoup(driver.page_source, 'html.parser')
            
        except (TimeoutException, WebDriverException) as e:
            logging.warning(f"Attempt {attempt + 1} failed for {url}. Retrying...")
            time.sleep(5)
            
    logging.error(f"Failed to load {url} after {MAX_RETRIES} attempts.")
    return None

def extract_job_links(driver, category_url):
    """استخراج لینک تمام آگهی‌های شغلی با فیلتر ۱ هفته اخیر"""
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
            
            # آیا این لینک یک آگهی شغلی است؟
            is_job_link = ('/jobs/' in href and not href.startswith('http')) or \
                          ('/jobs/' in href and href.startswith('http') and 'jobvision.ir' in href)
                          
            if is_job_link:
                total_links_on_page += 1
                
                # پیدا کردن جعبه اصلی آگهی برای خواندن تاریخ آن (حرکت به سمت لایه‌های بالاتر HTML)
                parent = a_tag
                for _ in range(5):
                    if parent.parent:
                        parent = parent.parent
                        if any(t in parent.get_text() for t in ["پیش", "امروز", "دیروز"]):
                            break
                
                card_text = parent.get_text()
                
                # فقط اگر آگهی جدید بود لینک آن را استخراج کن
                if is_recent_job(card_text):
                    full_url = f"https://jobvision.ir{href}" if not href.startswith('http') else href
                    job_links.add(full_url)
                    recent_links_found += 1
                
        logging.info(f"Found {recent_links_found} RECENT jobs out of {total_links_on_page} on page {page}.")
        
        # بهینه‌سازی هوشمند: 
        # اگر در صفحه آگهی وجود داشت اما هیچکدام برای ۱ هفته اخیر نبودند،
        # یعنی به آگهی‌های قدیمی رسیده‌ایم و نیازی به چک کردن صفحات بعدی نیست!
        if total_links_on_page > 0 and recent_links_found == 0:
            logging.info("All jobs on this page are older than 1 week. Stopping pagination for this category.")
            break
            
        if total_links_on_page == 0:
            logging.info("No jobs found on page. Ending pagination.")
            break
            
    return list(job_links)
def extract_job_details(driver, job_url):
    """استخراج جزئیات دقیق هر آگهی با تمرکز ویژه بر شرح شغل و وظایف"""
    soup = safe_get(driver, job_url)
    if not soup:
        return None

    try:
        # 1. استخراج عنوان شغل
        title = "N/A"
        title_element = soup.find('h1')
        if title_element:
            title = clean_persian_text(title_element.get_text())

        # 2. استخراج شهر (با دو روش برای قالب‌های مختلف)
        city = "N/A"
        city_element = soup.find(lambda tag: tag.name == "span" and "استخدام در" in tag.text)
        if city_element:
            city = clean_persian_text(city_element.get_text().replace("استخدام در", ""))
        else:
            # روش جایگزین: جستجو در اطلاعات هدر
            header_details = soup.find_all('div', class_=re.compile(r'text-black'))
            for detail in header_details:
                text = detail.get_text()
                if any(keyword in text for keyword in ["تهران", "استان", "شهر "]):
                    city = clean_persian_text(text)
                    break

        # 3. استخراج دقیق "شرح شغل و وظایف" با استفاده از ساختار HTML
        description = "N/A"
        
        # پیدا کردن تگ H2 که عنوان "شرح شغل و وظایف" را دارد
        desc_header = soup.find(lambda tag: tag.name == "h2" and 
                                ("شرح شغل" in tag.text or "وظایف" in tag.text))
        
        if desc_header:
            # پیدا کردن المانِ برادرِ بعدی (تگی که بلافاصله بعد از H2 می‌آید)
            # در ساختار جاب‌ویژن، این معمولاً یک div است که شامل محتوای اصلی است.
            content_div = desc_header.find_next_sibling('div')
            
            if content_div:
                # تبدیل تگ‌های <br> به اسپیس یا خط تیره برای خوانایی بهتر در اکسل
                for br in content_div.find_all("br"):
                    br.replace_with(" | ") 
                
                # استخراج متن نهایی و پاک‌سازی آن
                description = clean_persian_text(content_div.get_text())
            else:
                 # اگر برادر بعدی پیدا نشد، سعی می‌کنیم والدش را بگیریم
                 description = clean_persian_text(desc_header.parent.get_text(separator=" | "))
        else:
            # پشتیبان نهایی برای قالب‌های قدیمی‌تر
            fallback_container = soup.find('div', class_=re.compile(r'description|details|req', re.I))
            if fallback_container:
                 description = clean_persian_text(fallback_container.get_text(separator=" | "))

        # حذف عنوان از ابتدای متن استخراج شده
        description = description.replace("شرح شغل و وظایف | ", "").replace("شرح شغل | ", "").strip()

        return {
            'title': title,
            'city': city,
            'description_and_responsibilities': description,
            'url': job_url
        }
    except Exception as e:
        logging.error(f"Error parsing job details for {job_url}: {e}")
        return None
def init_csv():
    """ساخت فایل اکسل با فرمت UTF-8-SIG برای نمایش صحیح زبان فارسی"""
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['title', 'city', 'description_and_responsibilities', 'url'])
        if not file_exists:
            writer.writeheader()

def save_job_incrementally(job_data):
    """ذخیره لحظه‌ای هر آگهی در فایل برای جلوگیری از دست رفتن داده‌ها در صورت قطعی"""
    if not job_data:
        return
        
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['title', 'city', 'description_and_responsibilities', 'url'])
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
    
    # بررسی آگهی‌هایی که قبلا ذخیره شده‌اند تا دوباره بررسی نشوند
    if os.path.isfile(CSV_FILE):
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed_urls.add(row['url'])
                
    init_csv()

    try:
        logging.info("Starting Selenium WebDriver...")
        driver = setup_driver()

        # مرحله اول: پیدا کردن لینک تمام آگهی‌ها
        for category in CATEGORIES:
            links = extract_job_links(driver, category)
            all_job_links.update(links)
            
        stats['total_found'] = len(all_job_links)
        logging.info(f"Total unique jobs found across categories: {stats['total_found']}")

        # مرحله دوم: باز کردن تک‌تک آگهی‌ها و استخراج اطلاعات
        for idx, url in enumerate(all_job_links, 1):
            if url in processed_urls:
                logging.info(f"[{idx}/{stats['total_found']}] Skipping already processed job: {url}")
                continue
                
            logging.info(f"[{idx}/{stats['total_found']}] Processing: {url}")
            job_data = extract_job_details(driver, url)
            
            if job_data and job_data['title'] != "N/A":
                save_job_incrementally(job_data)
                processed_urls.add(url)
                stats['successful'] += 1
            else:
                stats['failed'] += 1

    except KeyboardInterrupt:
        logging.warning("\nScript interrupted by user. Saving progress and exiting...")
    finally:
        if driver:
            driver.quit()
            
        # نمایش گزارش نهایی
        print("\n" + "="*40)
        print("          SCRAPING SUMMARY")
        print("="*40)
        print(f"Total Job Links Found:  {stats['total_found']}")
        print(f"Successfully Extracted: {stats['successful']}")
        print(f"Failed Extractions:     {stats['failed']}")
        print(f"Total Duplicates Skipped (From previous runs): {len(processed_urls) - stats['successful']}")
        print("="*40)
        print(f"Data saved to {CSV_FILE}")

if __name__ == "__main__":
    main()