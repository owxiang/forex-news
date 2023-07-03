# Daily Forex News Alert

Web Scraping with Selenium.

Using Repo **Secrets** and **Variables**. [See setting](https://github.com/owxiang/forex-news/settings/secrets/actions).

[YAML initialisation at env](https://github.com/owxiang/forex-news/blob/main/.github/workflows/main.yml)
```
TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
TELEGRAM_CHANNEL_ID: ${{ secrets.TELEGRAM_CHANNEL_ID }}
URL: ${{ vars.URL }}
```

[Python initialisation](https://github.com/owxiang/forex-news/blob/main/main.py)
```
bot = os.environ['TELEGRAM_BOT_TOKEN']
chat_id = os.environ['TELEGRAM_CHANNEL_ID']
url = os.environ['URL']
```
