from urllib.parse import quote
from dateutil.tz import gettz
from datetime import datetime, timedelta
import os
import requests
import datetime
import boto3
import re

ssm = boto3.client('ssm')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('forex-news-alert')


def remove_lambda_trigger(lambda_arn, rule_name):
    lambda_client = boto3.client('lambda')
    statement_id = f'{rule_name}-Event'
    
    try:
        lambda_client.remove_permission(
            FunctionName=lambda_arn,
            StatementId=statement_id
        )
    except lambda_client.exceptions.ResourceNotFoundException:
        # Ignore the error if the permission does not exist
        pass
    
    
def create_cloudwatch_event(name, description, schedule_expression, lambda_arn):
    events_client = boto3.client('events')
    lambda_client = boto3.client('lambda')
    
    rule_response = events_client.put_rule(
        Name=name,
        ScheduleExpression=schedule_expression,
        State='ENABLED',
        Description=description
    )
    
    statement_id = f'{name}-Event'
    
    # Try to remove existing permission if it exists
    try:
        lambda_client.remove_permission(
            FunctionName=lambda_arn,
            StatementId=statement_id,
        )
    except lambda_client.exceptions.ResourceNotFoundException:
        # Ignore the error if the permission does not exist
        pass
    
    # Add a new permission
    lambda_client.add_permission(
        FunctionName=lambda_arn,
        StatementId=statement_id,
        Action='lambda:InvokeFunction',
        Principal='events.amazonaws.com',
        SourceArn=rule_response['RuleArn']
    )

    events_client.put_targets(
        Rule=name,
        Targets=[
            {
                'Arn': lambda_arn,
                'Id': 'target-id-1',
            },
        ]
    )


def extend_cloudwatch_event(rule_name):
    events_client = boto3.client('events')

    try:
        response = events_client.describe_rule(Name=rule_name)
        schedule_expression = response['ScheduleExpression']
        
        # Remove 'cron(' at the beginning and ')' at the end
        schedule_expression = schedule_expression.replace('cron(', '').replace(')', '')
        
        fields = schedule_expression.split(' ')
        original_minute = int(fields[0])
        original_hour = int(fields[1])
        original_day = int(fields[2])
        original_month = int(fields[3])
        original_year = int(fields[5])
        
        # Construct a datetime object
        original_time = datetime(year=original_year, month=original_month, day=original_day, hour=original_hour, minute=original_minute)
        
        # Add 30 minutes
        new_time = original_time + timedelta(minutes=30)
        
        # Update fields
        fields[0] = str(new_time.minute)
        fields[1] = str(new_time.hour)
        fields[2] = str(new_time.day)
        fields[3] = str(new_time.month)
        fields[5] = str(new_time.year)
        
        new_schedule_expression = 'cron(' + ' '.join(fields) + ')'
        
        events_client.put_rule(
            Name=rule_name,
            ScheduleExpression=new_schedule_expression,
            State='ENABLED'
        )
        
    except events_client.exceptions.ResourceNotFoundException:
        # The rule does not exist or was deleted, handle the error here if needed.
        pass

def delete_cloudwatch_event(name):
    events_client = boto3.client('events')
    events_client.remove_targets(Rule=name, Ids=['target-id-1'])
    events_client.delete_rule(Name=name)
    
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
    message = quote(message)  # URL-encode the message
    send_text = f'https://api.telegram.org/{bot_token}/sendMessage?chat_id={chat_id}&parse_mode=Markdown&text={message}'
    if reply_to_message_id:
        send_text += f'&reply_to_message_id={reply_to_message_id}'
    response = requests.get(send_text)
    return response.json()

def get_parameters_from_ssm():
    bot_token = ssm.get_parameter(Name='telagram-bot-token-coderautobot', WithDecryption=True)['Parameter']['Value']
    chat_id = ssm.get_parameter(Name='telagram-chatid-trade-watch')['Parameter']['Value']
    return bot_token, chat_id

def set_pre_event_schedule(row, event_time, lambda_arn):
    event_name = re.sub('[^a-zA-Z0-9]', '_', row['Event'])  # Replace anything not a-zA-Z0-9 with underscore (_)
    rule_name = f'forex_schedule_{event_name}_pre'
    event_time_utc = (event_time - datetime.timedelta(minutes=5)).astimezone(datetime.timezone.utc)
    event_time_hour_utc = event_time_utc.hour
    event_time_minute_utc = event_time_utc.minute
    schedule_expression = f'cron({event_time_minute_utc} {event_time_hour_utc} {event_time.day} {event_time.month} ? {event_time.year})'

    create_cloudwatch_event(rule_name, 'Pre-Event Message Trigger', schedule_expression, lambda_arn)
    print(f"EventBridge Schedule {rule_name} {schedule_expression} is created and its permission is added.")

def send_pre_event_message(row, bot_token, chat_id, lambda_arn):
    message = f"*High Impact News in 5 Minutes*\n\nEvent: {row['Event']}\nCurrency: {row['Currency']}"
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

    event_name = re.sub('[^a-zA-Z0-9]', '_', row['Event'])  # Replace anything not a-zA-Z0-9 with underscore (_)
    rule_name = f'forex_schedule_{event_name}_pre'
    
    remove_lambda_trigger(lambda_arn, rule_name)
    delete_cloudwatch_event(rule_name)
    print(f"EventBridge Schedule {rule_name} is deleted its permission is removed.")
    # set_post_event_schedule(event_name,event_time)

def set_post_event_schedule(event_name,event_time):
    rule_name = f'forex_schedule_{event_name}_post'
    event_time_utc = (event_time + datetime.timedelta(minutes=30)).astimezone(datetime.timezone.utc)
    event_time_hour_utc = event_time_utc.hour
    event_time_minute_utc = event_time_utc.minute
    schedule_expression = f'cron({event_time_minute_utc} {event_time_hour_utc} {event_time.day} {event_time.month} ? {event_time.year})'
    
    create_cloudwatch_event(rule_name, 'Post-Event Message Trigger', schedule_expression, lambda_arn)

def send_post_event_message(row, bot_token, chat_id, lambda_arn):
    item = table.get_item(Key={'event': row['Event']}).get('Item', {})
    event_name = re.sub('[^a-zA-Z0-9]', '_', row['Event'])  # Replace anything not a-zA-Z0-9 with underscore (_)
    rule_name = f'forex_schedule_{event_name}_post'
    
    if item and row['Actual']:
        message = f"Event: {row['Event']}\nCurrency: {row['Currency']}\nActual: {row['Actual']}\nForecast: {row['Forecast']}\nPrevious: {row['Previous']}"
        message_id = item.get('message_id')
        if message_id:
            send_telegram_message(bot_token, chat_id, message, reply_to_message_id=int(message_id))
            
            # Delete the item from DynamoDB
            table.delete_item(Key={'event': row['Event']})

            remove_lambda_trigger(lambda_arn, rule_name)
            delete_cloudwatch_event(rule_name)
    else:
        # Extend schedule 30 mins because row['Actual'] is not presented
        extend_cloudwatch_event(rule_name)
        
def send_post_event_message_v2(row, bot_token, chat_id):
    item = table.get_item(Key={'event': row['Event']}).get('Item', {})
    
    if item and row['Actual']:
        message = f"Event: {row['Event']}\nCurrency: {row['Currency']}\nActual: {row['Actual']}\nForecast: {row['Forecast']}\nPrevious: {row['Previous']}"
        message_id = item.get('message_id')

        send_telegram_message(bot_token, chat_id, message, reply_to_message_id=int(message_id))
    table.delete_item(Key={'event': row['Event']})
    print(f"{item} is deleted from DynamoDB.")
        
def lambda_handler(event, context):
    github_readme_url = "https://raw.githubusercontent.com/owxiang/forex-news/main/news.high.md"
    readme_content = fetch_github_readme_content(github_readme_url)
    lambda_arn = context.invoked_function_arn

    # Extract the date from the markdown content
    date_str = re.findall(r"## (.*?) - High Impact Forex News", readme_content)[0]
    
    table_data = extract_table_data(readme_content, date_str)
    if not table_data:
        return {
            'statusCode': 200,
            'body': 'No high impact news found. Exiting Lambda function.'
        }

    bot_token, chat_id = get_parameters_from_ssm()
    current_time = datetime.datetime.now(tz=gettz('GMT+8'))
    time_zone = gettz('GMT+8')

    for row in table_data:

        # check if lambda is triggered by eventbridge
        if 'resources' in event:
            clean_event_name = re.sub('[^a-zA-Z0-9]', '', row['Event'])
            rule_name = event['resources'][0].split('/')[-1]
            clean_rule_name = re.sub('[^a-zA-Z0-9]', '', rule_name)
            
            if rule_name == 'schedule-forex-before-after-news-alert':
                event_time_str = row['Time (GMT+8)']
                event_time = datetime.datetime.strptime(event_time_str, '%d %B %Y - %H:%M').replace(tzinfo=time_zone)
                set_pre_event_schedule(row, event_time, lambda_arn)
                
            elif rule_name == 'schedule-forex-before-after-news-alert-eod':
                send_post_event_message_v2(row, bot_token, chat_id)
                
            elif '_pre' in rule_name:
                if clean_event_name in clean_rule_name:
                    send_pre_event_message(row, bot_token, chat_id, lambda_arn)
        else:
            rule_name = None
      
    return {
        'statusCode': 200,
        'body': 'Success!'
    }
