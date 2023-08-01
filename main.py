from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from datetime import datetime
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
    # chromedriver_path = '/path/to/chromedriver'
    # chromedriver_path = os.getenv('CHROMEWEBDRIVER')

    # Set Chrome options to run in headless mode
    # chrome_options = Options()
    # chrome_options.add_argument('--headless')  # Run Chrome in headless mode
    # options = webdriver.ChromeOptions()

    # Start the ChromeDriver service
    # service = Service(chromedriver_path)
    # service = Service()

    # Start the WebDriver
    # driver = webdriver.Chrome(service=service, options=chrome_options)
    # driver = webdriver.Chrome(service=service, options=options)
    driver = webdriver.Chrome()

    # Load the webpage
    # timezone = 27 = GMT+8
    driver.get(url)

    # Wait for the table to load (adjust the wait time as needed)
    driver.implicitly_wait(10)

    # Find the date element
    date_element = driver.find_element(By.CLASS_NAME, 'theDay')
    
    # Extract the date
    date_str = date_element.text.strip()
    
    # Convert the string to a datetime object
    date_obj = datetime.strptime(date_str, "%A, %B %d, %Y")
    
    # Format the datetime object as a string in the desired format
    formatted_date = date_obj.strftime("%d %B %Y")

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
        
    write_to_md(table_for_all_md,table_for_high_md,table_for_moderate_md,table_for_low_md,table_header_for_all,table_header_for_the_rest,formatted_date)

    if not high_events:
        message = f"There is no high impact news on {formatted_date}.\n\n"
    else:
        message = f"{formatted_date} Forex High Impact News Alert in GMT+8\n\n{high_events}"
        
    current_hour = datetime.now().hour
    if current_hour == 21: # 0500 (GMT+8) = 2100 (GMT+0)
        send_telegram(message)

    # Close the WebDriver
    driver.quit()
    
def send_telegram(message):
    # Initialize
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
    
def write_to_md(table_for_all_md, table_for_high_md, table_for_moderate_md, table_for_low_md, table_header_for_all, table_header_for_the_rest, formatted_date):
    table_content = {
        'table_for_all_md.txt': table_for_all_md,
        'table_for_high_md.txt': table_for_high_md,
        'table_for_moderate_md.txt': table_for_moderate_md,
        'table_for_low_md.txt': table_for_low_md
    }

    headers = {
        'table_for_all_md.txt': f"## {formatted_date} - All Forex News",
        'table_for_high_md.txt': f"## {formatted_date} - High Impact Forex News",
        'table_for_moderate_md.txt': f"## {formatted_date} - Moderate Impact Forex News",
        'table_for_low_md.txt': f"## {formatted_date} - Low Impact Forex News"
    }

    no_news_messages = {
        'table_for_all_md.txt': "There is no news today.",
        'table_for_high_md.txt': "There is no high impact news today.",
        'table_for_moderate_md.txt': "There is no moderate impact news today.",
        'table_for_low_md.txt': "There is no low impact news today."
    }

    for filename, content in table_content.items():
        if content == table_header_for_all or content == table_header_for_the_rest:
            content = no_news_messages[filename]
        
        # Add formatted_date to the content
        content = f"{headers[filename]}\n\n{content}"
        
        with open(filename, 'w') as file:
            file.write(content)


scrape_forex_events()
