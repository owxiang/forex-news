from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime
import requests
import os

def initialize_table():
    table_header_for_all = "| Time (GMT+8) | Currency | Importance | Event | Actual | Forecast | Previous |\n|------|----------|------------|-------|--------|----------|----------|\n"
    table_header_for_the_rest = "| Time (GMT+8) | Currency | Event | Actual | Forecast | Previous |\n|------|----------|-------|--------|----------|----------|\n"
    return table_header_for_all, table_header_for_the_rest

def initialize_webdriver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')  
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def get_date(driver):
    date_element = driver.find_element(By.CLASS_NAME, 'theDay')
    date_str = date_element.text.strip()
    date_obj = datetime.strptime(date_str, "%A, %B %d, %Y")
    formatted_date = date_obj.strftime("%d %B %Y")
    return formatted_date

def get_event_rows(driver):
    table = driver.find_element(By.ID, 'ecEventsTable')
    event_rows = table.find_elements(By.TAG_NAME, 'tr')
    return event_rows

def process_event_row(event_row):
    cells = event_row.find_elements(By.TAG_NAME, 'td')
    if len(cells) >= 8:
        time = cells[0].text.strip()
        currency = cells[1].text.strip()
        sentiment = cells[2].get_attribute('title')
        event = cells[3].text.strip()
        actual = cells[4].text.strip()
        forecast = cells[5].text.strip()
        previous = cells[6].text.strip()
        return time, currency, sentiment, event, actual, forecast, previous
    return None

def write_to_readme(table_for_all_readme,table_for_high_readme,table_for_moderate_readme,table_for_low_readme,table_header_for_all,table_header_for_the_rest,formatted_date):
    with open('README.md', 'w') as f:
        f.write(f"# Forex Calendar Events for {formatted_date}\n\n")
        f.write("## All Events\n\n")
        f.write(table_for_all_readme)
        f.write("\n\n## High Impact Events\n\n")
        if table_for_high_readme == table_header_for_the_rest:
            f.write("No high impact events for today.\n")
        else:
            f.write(table_for_high_readme)
        f.write("\n\n## Moderate Impact Events\n\n")
        if table_for_moderate_readme == table_header_for_the_rest:
            f.write("No moderate impact events for today.\n")
        else:
            f.write(table_for_moderate_readme)
        f.write("\n\n## Low Impact Events\n\n")
        if table_for_low_readme == table_header_for_the_rest:
            f.write("No low impact events for today.\n")
        else:
            f.write(table_for_low_readme)

def scrape_forex_events():
    url = os.environ['URL']
    all_events = ""
    high_events = ""
    moderate_events = "" 
    low_events = ""       
    table_header_for_all, table_header_for_the_rest = initialize_table()
    table_for_all_readme = table_header_for_all
    table_for_low_readme = table_for_moderate_readme = table_for_high_readme = table_header_for_the_rest
    driver = initialize_webdriver()
    driver.get(url)
    driver.implicitly_wait(10)
    formatted_date = get_date(driver)
    event_rows = get_event_rows(driver)
    for event_row in event_rows:
        event_data = process_event_row(event_row)
        if event_data:
            time, currency, sentiment, event, actual, forecast, previous = event_data
            if "High Volatility Expected" in sentiment:
                high_events += f"Time: {time}\nCurrency: {currency}\nEvent: {event}\nForecast: {forecast}\nPrevious: {previous}\n\n"
                table_for_high_readme += f"| {time} | {currency} | {event} | {actual} | {forecast} | {previous} |\n"
                sentiment = "High"
            elif "Moderate Volatility Expected" in sentiment:
                moderate_events += f"Time: {time}\nCurrency: {currency}\nEvent: {event}\nForecast: {forecast}\nPrevious: {previous}\n\n"
                table_for_moderate_readme += f"| {time} | {currency} | {event} | {actual} | {forecast} | {previous} |\n"
                sentiment = "Moderate"
            elif "Low Volatility Expected" in sentiment:
                low_events += f"Time: {time}\nCurrency: {currency}\nEvent: {event}\nForecast: {forecast}\nPrevious: {previous}\n\n"
                table_for_low_readme += f"| {time} | {currency} | {event} | {actual} | {forecast} | {previous} |\n"
                sentiment = "Low"
            all_events += f"Time: {time}\nCurrency: {currency}\nImportance: {sentiment}\nEvent: {event}\nActual: {actual}\nForecast: {forecast}\nPrevious: {previous}\n\n"
            table_for_all_readme += f"| {time} | {currency} | {sentiment} | {event} | {actual} | {forecast} | {previous} |\n"
            
    write_to_readme(table_for_all_readme,table_for_high_readme,table_for_moderate_readme,table_for_low_readme,table_header_for_all,table_header_for_the_rest,formatted_date)
    
    if not high_events:
        message = f"There is no high impact news on {formatted_date}.\n\n"
    else:
        message = f"{formatted_date} Forex High Impact News Alert in GMT+8\n\n{high_events}"
    current_hour = datetime.now().hour
    send_hour = 10 # 0100 (GMT+8) = 1700 (GMT+0)
    if current_hour == send_hour:
        send_telegram(message)
    
def send_telegram(message):
    bot = os.environ['TELEGRAM_BOT_TOKEN']
    chat_id = os.environ['TELEGRAM_CHANNEL_ID']
    
    telegram_url = f"https://api.telegram.org/{bot}/sendMessage"
    pin_message_url = f"https://api.telegram.org/{bot}/pinChatMessage"

    params = {
        "chat_id": chat_id,
        "text": message+  "[forex-news](https://github.com/owxiang/forex-news)",
        "parse_mode": "markdown",
        "disable_web_page_preview": True
    }
    response = requests.get(telegram_url, params=params)
    if response.status_code == 200:
        message_id = response.json()["result"]["message_id"]
        pin_params = {
            "chat_id": chat_id,
            "message_id": message_id,
            "disable_notification": True
        }
        pin_response = requests.get(pin_message_url, params=pin_params)
        
        if pin_response.status_code == 200:
            print("Telegram message sent and pinned successfully!")
        else:
            print(f"Telegram message sent successfully but failed to pin. Status code: {pin_response.status_code}. Error message: {pin_response.text}")
    else:
        print(f"Telegram message failed. Status code: {response.status_code}. Error message: {response.text}")
   
scrape_forex_events()
