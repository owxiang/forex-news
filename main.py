from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from datetime import datetime
import requests
import os

def initialize_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')  
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def format_date(driver):
    date_element = driver.find_element(By.CLASS_NAME, 'theDay')
    date_str = date_element.text.strip()
    date_obj = datetime.strptime(date_str, "%A, %B %d, %Y")
    return date_obj.strftime("%d %B %Y")

def scrape_events(driver):
    table = driver.find_element(By.ID, 'ecEventsTable')
    return table.find_elements(By.TAG_NAME, 'tr')

def process_event_row(event_row):
    cells = event_row.find_elements(By.TAG_NAME, 'td')
    if len(cells) < 8:
        return None
    return {
        "time": cells[0].text.strip(),
        "currency": cells[1].text.strip(),
        "sentiment": cells[2].get_attribute('title'),
        "event": cells[3].text.strip(),
        "actual": cells[4].text.strip(),
        "forecast": cells[5].text.strip(),
        "previous": cells[6].text.strip()
    }

def write_to_readme(content_dict, formatted_date):
    base_header = f"## {formatted_date} - {content_dict['name']} Forex News"
    if not content_dict['events']:
        content = f"{base_header}\n\nThere is no {content_dict['impact'].lower()} impact news today."
    else:
        content = f"{base_header}\n\n{content_dict['table']}"
    with open(content_dict['filename'], 'w') as file:
        file.write(content)
        
def send_telegram(message):
    bot = os.environ['TELEGRAM_BOT_TOKEN']
    chat_id = os.environ['TELEGRAM_CHANNEL_ID']
    telegram_url = f"https://api.telegram.org/{bot}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "markdown",
        "disable_web_page_preview": True
    }
    response = requests.get(telegram_url, params=params)
    if response.status_code == 200:
        print("Telegram message sent successfully!")
    else:
        print(f"Telegram message failed. Status code: {response.status_code}. Error message: {response.text}")
        
def scrape_forex_events():
    url = os.environ['URL']
    driver = initialize_driver()
    driver.get(url)
    driver.implicitly_wait(10)
    formatted_date = format_date(driver)
    event_rows = scrape_events(driver)

    headers = {
        "All": "| Time (GMT) | Currency | Importance | Event | Actual | Forecast | Previous |\n|------|----------|------------|-------|--------|----------|----------|\n",
        "Impact": "| Time (GMT) | Currency | Event | Actual | Forecast | Previous |\n|------|----------|-------|--------|----------|----------|\n"
    }

    content_dict = {
        'All': {'events': [], 'table': headers['All'], 'filename': 'table_for_all_readme.txt', 'impact': 'All', 'name': 'All'},
        'High': {'events': [], 'table': headers['Impact'], 'filename': 'table_for_high_readme.txt', 'impact': 'High', 'name': 'High Impact'},
        'Moderate': {'events': [], 'table': headers['Impact'], 'filename': 'table_for_moderate_readme.txt', 'impact': 'Moderate', 'name': 'Moderate Impact'},
        'Low': {'events': [], 'table': headers['Impact'], 'filename': 'table_for_low_readme.txt', 'impact': 'Low', 'name': 'Low Impact'}
    }
    
    for event_row in event_rows:
        event_data = process_event_row(event_row)
        if event_data:
            sentiment = event_data['sentiment']
            impact_level = "Low"
            if "High Volatility Expected" in sentiment:
                impact_level = "High"
            elif "Moderate Volatility Expected" in sentiment:
                impact_level = "Moderate"
            elif "Low Volatility Expected" in sentiment:
                impact_level = "Low"

            event_data['importance'] = impact_level
            content_dict[impact_level]['events'].append(event_data)  
            content_dict['All']['events'].append(event_data)  
            
                
    for key, value in content_dict.items():
        if key == 'All':
            row_format = "| {time} | {currency} | {importance} | {event} | {actual} | {forecast} | {previous} |\n"
        else:
            row_format = "| {time} | {currency} | {event} | {actual} | {forecast} | {previous} |\n"

        for event in value['events']:
            value['table'] += row_format.format(**event)
        write_to_readme(value, formatted_date)
        
    driver.quit()

scrape_forex_events()
