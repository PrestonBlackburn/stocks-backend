import boto3
import json
from boto3.dynamodb.conditions import Key, Attr
import datetime
import pandas as pd

#lambda function
dynamodb = boto3.resource('dynamodb')


def scan_items(ticker):
    table = dynamodb.Table('processed-sentences-testing-1')
    scan_kwargs = {
        'FilterExpression': Key('ticker').begins_with(ticker),
        'ProjectionExpression': "articleTitle, #dt, sentiment, ticker",
        'ExpressionAttributeNames': {"#dt": "date"}
    }
    # could also do between dates 'FilterExpresion': Key('dt').between(date1, date2),
    # need to define expression attribute name since date is reserved
    done = False
    start_key = None
    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        response = table.scan(**scan_kwargs)
        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None
    return response

def scan_all_items():
    table = dynamodb.Table('processed-sentences-testing-1')
    scan_kwargs = {
        'ProjectionExpression': "articleTitle, #dt, sentiment, ticker",
        'ExpressionAttributeNames': {"#dt": "date"}
    }
    done = False
    start_key = None
    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        response = table.scan()
        #display_response(response.get('Items', []))
        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None
    return response


def get_all_data_handler(event, context):
    print(event)

    #print(event)
    # POST Request Info
    '''
    try:
        input_request = json.loads(event['body'])
    except:
        input_request = event['body']
    print(input_request)

    try: 
        input_request = input_request[0]
    except:
        pass
    print(input_request)
    '''

    #Fetch Data
    #query_data = scan_items(input_request['ticker'])
    query_data = scan_all_items()
    query_result = query_data['Items']

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(
            {
                "db_results": query_result,
            }
        )
    }

def get_weekly_data_handler(event, context):
    print(event)
    # POST Request Info
    ''''
    try:
        input_request = json.loads(event['body'])
    except:
        input_request = event['body']
    print(input_request)

    try: 
        input_request = input_request[0]
    except:
        pass
    print(input_request)
    '''

    #Fetch Data
    query_data = scan_all_items()
    query_result = query_data['Items']

    #Format As Weekly Data
    df = pd.DataFrame(query_result)
    df['sentiment'] = df['sentiment'].astype('float64') 
    df['date'] = pd.to_datetime(df['date'])
    df_2 = df.set_index("date")
    weekly_avg = df_2.resample("W").mean()
    weekly_avg = weekly_avg.reset_index()
    weekly_avg['date'] = weekly_avg['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    weekly_avg['sentiment'] = weekly_avg['sentiment'].apply(lambda x: str(x))
    weekly_response = list(weekly_avg.T.to_dict().values())

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(
            {
                "db_results": weekly_response,
            }
        )
    }











