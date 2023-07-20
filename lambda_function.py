import os
import requests
import datetime
import boto3
import re
from dateutil.tz import gettz
import json

ssm = boto3.client('ssm')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('forex-news-alert')

def lambda_handler(event, context):
    github_readme_url = "https://raw.githubusercontent.com/owxiang/forex-news/main/news.high.md"
    readme_content = fetch_github_readme_content(github_readme_url)

    # Extract the date from the markdown content
    date_str = re.findall(r"## (.*?) - High Impact Forex News", readme_content)[0]
    
    table_data = extract_table_data(readme_content, date_str)

    if not table_data:
        return {
            'statusCode': 200,
            'body': 'No high impact news found. Exiting Lambda function.'
        }

    # Retrieve bot token and chat id from AWS SSM
    bot_token = ssm.get_parameter(Name='telagram-bot-token-coderautobot', WithDecryption=True)['Parameter']['Value']
    chat_id = ssm.get_parameter(Name='telagram-chatid-marketsiren')['Parameter']['Value']

    current_time = datetime.datetime.now(tz=gettz('GMT+8'))
    time_zone = gettz('GMT+8')

    for row in table_data:
        event_time_str = row['Time (GMT+8)']
        event_time = datetime.datetime.strptime(event_time_str, '%d %b %Y - %H:%M').replace(tzinfo=time_zone)
        time_difference = event_time - current_time

        # Send pre-event message 5 minutes before the event
        if time_difference.total_seconds() > 0 and time_difference.total_seconds() <= 300:
            message = f"*High Impact News Alert in 5 Minutes*\n\nEvent: {row['Event']}\nCurrency: {row['Currency']}"
            pre_event_message_response = send_telegram_message(bot_token, chat_id, message)
            pre_event_message_id = pre_event_message_response['result']['message_id']

            # Store the message_id and event in DynamoDB
            table.put_item(
                Item={
                    'event': row['Event'],
                    'message_id': str(pre_event_message_id),
                    'timestamp': datetime.datetime.now().isoformat(),
                }
            )
            
        # Get the item from DynamoDB
        item = table.get_item(Key={'event': row['Event']}).get('Item', {})
        
        # Send post-event message after the event
        if row['Actual'] and item:
            message = f"Event: {row['Event']}\nCurrency: {row['Currency']}\nActual: {row['Actual']}\nForecast: {row['Forecast']}\nPrevious: {row['Previous']}"
            message_id = item.get('message_id')
            if message_id:
                send_telegram_message(bot_token, chat_id, message, reply_to_message_id=int(message_id))
                
                # Delete the item from DynamoDB
                table.delete_item(Key={'event': row['Event']})

    return {
        'statusCode': 200,
        'body': 'Success!'
    }
    
def fetch_github_readme_content(url):
    headers = {
        "Accept": "application/vnd.github.v3.raw"  # Set the accept header for raw content
    }
    response = requests.get(url, headers=headers)
    return response.text

def extract_table_data(content, date_str):
    table_data = []
    lines = content.split('\n')

    # Find the table rows using regular expressions
    table_rows = re.findall(r'\|.*\|', content)

    # Exit if no table rows are detected
    if len(table_rows) < 3:
        return table_data

    # Extract the table headers
    headers = [header.strip() for header in table_rows[0].split('|')[1:-1]]

    # Extract the table data for each row
    for row in table_rows[2:]:
        cells = [cell.strip() for cell in row.split('|')[1:-1]]
        data = {headers[i]: cell for i, cell in enumerate(cells)}
        
        # Append the date to the time entry
        data['Time (GMT+8)'] = date_str + " - " + data['Time (GMT+8)']
        table_data.append(data)

    return table_data

def send_telegram_message(bot_token, chat_id, message, reply_to_message_id=None):
    send_text = f'https://api.telegram.org/{bot_token}/sendMessage?chat_id={chat_id}&parse_mode=Markdown&text={message}'
    if reply_to_message_id:
        send_text += f'&reply_to_message_id={reply_to_message_id}'
    response = requests.get(send_text)
    return response.json()
