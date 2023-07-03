from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import requests
import os

# Initialize Telegram bot
bot = os.environ['TELEGRAM_BOT_TOKEN']
chat_id = os.environ['TELEGRAM_CHANNEL_ID']
high_events = ""
moderate_events = ""
low_events = ""

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
url = 'https://ec.forexprostools.com/?columns=exc_currency,exc_importance&importance=1,2,3&calType=day&timeZone=27&lang=1'
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
    if len(cells) >= 4:
        time = cells[0].text.strip()
        currency = cells[1].text.strip()
        sentiment = cells[2].get_attribute('title')
        event = cells[3].text.strip()

        if "High Volatility Expected" in sentiment:
            high_events += f"Time: {time}\nCurrency: {currency}\nEvent: {event}\n\n"
        elif "Moderate Volatility Expected" in sentiment:
            moderate_events += f"Time: {time}\nCurrency: {currency}\nEvent: {event}\n\n"
        elif "Low Volatility Expected" in sentiment:
            low_events += f"Time: {time}\nCurrency: {currency}\nEvent: {event}\n\n"
        else:
            other_events += f"Time: {time}\nCurrency: {currency}\nEvent: {event}\n\n"
            
        # all_events += f"Time: {time}\nCurrency: {currency}\nImportance: {sentiment}\nEvent: {event}\n\n"

events_message = f"Daily Forex News Alert (SGT)\n\n**Low Impact**\n\n{low_events}\n\n**Moderate Impact**\n\n{moderate_events}\n\n**High Impact**\n\n{high_events}\n\n**Others**\n\n{other_events}"

requests.get(
    f"https://api.telegram.org/{bot}/sendMessage?chat_id={chat_id}&text="
    + f"{events_message}"
    + "&parse_mode=markdown&disable_web_page_preview=True"
)

# print(all_events)
# Close the WebDriver
driver.quit()


