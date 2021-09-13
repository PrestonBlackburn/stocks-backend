#from transformers import PegasusTokenizer, TFPegasusForConditionalGeneration
#from transformers import pipeline
import tensorflow as tf
import tensorflow_text as text
import requests
import boto3
from datetime import datetime



#print(Test_Sentence)

#load tf model
saved_model_path = '/opt/ml/bertModel'
model = tf.saved_model.load(saved_model_path)


def output_examples(inputs, results):
    result_for_printing = \
        [f'input: {inputs[i]:<30} : score: {results[i][0]:.6f}'
                         for i in range(len(inputs))]
    print(*result_for_printing, sep='\n')
    output = [results[i][0].numpy() for i in range(len(inputs))]
    return output

def handle_insert(record):
    print("dynamodb stream started")
    newImage = record['dynamodb']['NewImage']
    print("newImage value", newImage)

    #parse values
    newSentence = newImage['sentence']['S']
    newTitle = newImage['articleTitle']['S']
    newTicker = newImage['ticker']['S']
    newURL = newImage['url']['S']
    print("newSentence Value", newSentence)

    #from TF model
    new_sentence_results = tf.sigmoid(model(tf.constant([newSentence])))
    new_sentiment = output_examples([newSentence], new_sentence_results)
    new_sentiment = str(new_sentiment[0].astype(float))
    return new_sentiment, newTitle, newTicker, newURL, newSentence


def write_to_dynamodb(url, title, ticker, sentence, sentiment):
    # need to import aws dynamodb package
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    add_time = datetime.today().strftime('%Y-%m-%d')
    table = dynamodb.Table('processed-sentences-testing-1')
    print(table.table_status)
    put_response = table.put_item(
    Item={
        'sentenceID':  url,
        'articleTitle': title,
        'ticker': ticker,
        'sentence': sentence,
        'sentiment': sentiment,
        'date': add_time
        }
    )
    return put_response


# Testing
Test_Sentence = ['At this growth rate , paying off the national debt will be extremely painful']
test_results = tf.sigmoid(model(tf.constant(Test_Sentence)))
output_examples(Test_Sentence, test_results)



def lambda_handler(event, context):
    print(event)
    try:
        # itterate over records
        for record in event['Records']:
            # handle event type
            if record['eventName'] == "INSERT":
                sentiment, newTitle, newTicker, newURL, newSentence = handle_insert(record)
                write_to_dynamodb(newURL, newTitle, newTicker, newSentence, sentiment)
    except Exception as e:
        print(e)
        return "something went wrong =("


    response = {
      'statusCode': 200,
      'body': 'successfully created item!',
      'headers': {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    }
    return response
