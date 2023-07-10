from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import requests
import os

def scrape_forex_events():
    # Initialize
    url = os.environ['URL']
    all_events = ""
    high_events = ""
    table_header_for_all = "| Time (GMT+8) | Currency | Importance | Event | Actual | Forecast | Previous |\n|------|----------|------------|-------|--------|----------|----------|\n"
    table_header_for_the_rest = "| Time (GMT+8) | Currency | Event | Actual | Forecast | Previous |\n|------|----------|-------|--------|----------|----------|\n"
    
    # Create a string variable to hold the table
    table_for_all_md = table_header_for_all
    table_for_low_md = table_for_moderate_md = table_for_high_md = table_header_for_the_rest
    
    # Path to the ChromeDriver executable
    chromedriver_path = '/path/to/chromedriver'

    # Set Chrome options to run in headless mode
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run Chrome in headless mode

    # Start the ChromeDriver service
    service = Service(chromedriver_path)

    # Start the WebDriver
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Load the webpage
    # timezone = 27 = GMT+8
    driver.get(url)

    # Wait for the table to load (adjust the wait time as needed)
    driver.implicitly_wait(10)

    # Find the table element
    table = driver.find_element(By.ID, 'ecEventsTable')

    # Find all the event rows in the table
    event_rows = table.find_elements(By.TAG_NAME, 'tr')

    # Iterate over the event rows and print the event details
    for event_row in event_rows:
        cells = event_row.find_elements(By.TAG_NAME, 'td')
        if len(cells) >= 8:
            time = cells[0].text.strip()
            currency = cells[1].text.strip()
            sentiment = cells[2].get_attribute('title')
            event = cells[3].text.strip()
            actual = cells[4].text.strip()
            forecast = cells[5].text.strip()
            previous = cells[6].text.strip()

            if "High Volatility Expected" in sentiment:
                high_events += f"Time: {time}\nCurrency: {currency}\nEvent: {event}\nForecast: {forecast}\nPrevious: {previous}\n\n"
                table_for_high_md += f"| {time} | {currency} | {event} | {actual} | {forecast} | {previous} |\n"
                sentiment = "High"
            elif "Moderate Volatility Expected" in sentiment:
                table_for_moderate_md += f"| {time} | {currency} | {event} | {actual} | {forecast} | {previous} |\n"
                sentiment = "Moderate"
            elif "Low Volatility Expected" in sentiment:
                table_for_low_md += f"| {time} | {currency} | {event} | {actual} | {forecast} | {previous} |\n"
                sentiment = "Low"
                
            all_events += f"Time: {time}\nCurrency: {currency}\nImportance: {sentiment}\nEvent: {event}\nActual: {actual}\nForecast: {forecast}\nPrevious: {previous}\n\n"
            table_for_all_md += f"| {time} | {currency} | {sentiment} | {event} | {actual} | {forecast} | {previous} |\n"
        
    write_to_md(table_for_all_md,table_for_high_md,table_for_moderate_md,table_for_low_md,table_header_for_all,table_header_for_the_rest)

    if not high_events:
        message = f"There is no high impact news today.\n\n"
    else:
        message = f"Daily Forex News Alert - High Impact - SGT\n\n{high_events}"
        
    send_telegram(message)

    # Close the WebDriver
    driver.quit()

def send_telegram(message):
    # Initialize
    bot = os.environ['TELEGRAM_BOT_TOKEN']
    chat_id = os.environ['TELEGRAM_CHANNEL_ID']
    
    if not bot or not chat_id:
        print("Telegram bot token or chat ID is not provided.")
        return
    
    telegram_url = f"https://api.telegram.org/bot{bot}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": f"{message} [forex-news](https://github.com/owxiang/forex-news)",
        "parse_mode": "markdown",
        "disable_web_page_preview": True
    }
    response = requests.get(telegram_url, params=params)
    print(response)
    print(response.status_code)
    
    if response.status_code != 200:
        print("Failed to send message via Telegram.")
        return
    print("Message sent successfully via Telegram.")

def write_to_md(table_for_all_md,table_for_high_md,table_for_moderate_md,table_for_low_md,table_header_for_all,table_header_for_the_rest):  
    files = {
        'table_for_all_md.txt': table_for_all_md,
        'table_for_high_md.txt': table_for_high_md,
        'table_for_moderate_md.txt': table_for_moderate_md,
        'table_for_low_md.txt': table_for_low_md
    }
    
    no_news_messages = {
        'table_for_all_md.txt': "There is no news today.",
        'table_for_high_md.txt': "There is no high impact news today.",
        'table_for_moderate_md.txt': "There is no moderate impact news today.",
        'table_for_low_md.txt': "There is no low impact news today."
    }
    
    for filename, content in files.items():
        if content == no_news_messages[filename]:
            content = f"{content}\n"
        with open(filename, 'w') as file:
            file.write(content)
        
scrape_forex_events()
