import json
import boto3
from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime
import random
import time


headers = { 
    'User-Agent'      : 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1', 
    'Accept'          : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 
    'Accept-Encoding': 'gzip, deflate, br',
    'pragma': 'no-cache',
    'referrer': 'https://google.com',
    'Accept-Language': 'en-US,en;q=0.9',
}

USER_AGENT_LIST = [
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.94 Chrome/37.0.2062.94 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/600.8.9 (KHTML, like Gecko) Version/8.0.8 Safari/600.8.9',
                    'Mozilla/5.0 (Windows NT 5.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/600.7.12 (KHTML, like Gecko) Version/7.1.7 Safari/537.85.16',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:39.0) Gecko/20100101 Firefox/39.0'
                ]

#update user agent for google occasionally
headers['User-Agent'] = random.choice(USER_AGENT_LIST)

#hardcode tickers for for testing
#tickers_exchange =  ['XOM:NYSE']

remove_title_text =["[", "<title>", "</title>", "]"]

def get_tickers():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table('ticker-symbols-testing-1')
    scan_kwargs = {
        'ProjectionExpression': "ticker",
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

def search_for_stock_news_urls(ticker):
    #looking at google finance:
    search_url = "https://www.google.com/finance/quote/{}".format(ticker)
    r = requests.get(search_url, headers=headers, timeout=5)
    soup = BeautifulSoup(r.text, 'html.parser')
    maintags = soup.find('main')
    atags = maintags.find_all('a')
    hrefs = [link['href'] for link in atags]
    linked_tickers = [ticker] * len(hrefs)
    delays = [0.52, 0.12, 0.36, 1.02, 0.15]
    delay = random.choice(delays)
    time.sleep(delay)
    return hrefs, linked_tickers

def strip_unwanted_urls(urls):
    val = []
    exclude_list = ['maps', 'policies', 'preferences', 'accounts', 'support', 'wiki', 'search', 'disclaimer', 'www.cdp.net']
    for url in urls: 
        if 'https://' in url and not any(exclude_word in url for exclude_word in exclude_list):
            res = re.findall(r'(https?://\S+)', url)[0].split('&')[0]
            val.append(res)
    return list(set(val))

def match_processed_urls(original_urls, cleaned_urls, tickers):
    new_ticker = []
    final_url = []
    for i in range(0, len(original_urls)):
        if any(item in original_urls[i] for item in cleaned_urls):
            final_url.append(original_urls[i])
            new_ticker.append(tickers[i])
    return final_url, new_ticker


def scrape_sentences_and_titles(URLs, ticker):
    all_titles = []
    sentences = []
    successful_URL = []
    successful_tickers = []
    for url in URLs:
        #add delay to be nice
        delays = [1.15, 1.82, 1.42, 1.36, 1.85]
        delay = random.choice(delays)
        time.sleep(delay)
        try:
            headers['User-Agent'] = random.choice(USER_AGENT_LIST)
            r = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(r.text, 'html.parser')
            # scrape away
            paragraphs = soup.find_all('p') 
            text = [paragraph.text for paragraph in paragraphs]
            words = ' '.join(text).split(' ')[:50]
            sentence = ' '.join(words)            
            title_tags = soup.find_all(["title"])
            title_text = [title.text for title in title_tags]
            short_title = ' '.join(title_text).split(' ')[:50]
            title = ' '.join(short_title)
            title = re.sub("|".join(sorted(remove_title_text, key = len, reverse = True)), "", str(title))
            # update those lists
            all_titles.append(title)
            sentences.append(sentence)
            successful_URL.append(url)
            successful_tickers.append(ticker[URLs.index(url)])
        except:
            continue    
    return all_titles, sentences, successful_URL, successful_tickers

def put_sentence(ticker, single_sentence, title, url):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    add_time = datetime.today().strftime('%Y-%m-%d')
    table = dynamodb.Table('crawled-data-testing-1')
    print(table.table_status)
    put_response = table.put_item(
    Item={
        'sentenceID':  url,
        'articleTitle': title,
        'url': url,
        'ticker': ticker,
        'sentence': single_sentence,
        'date': add_time
        }
    )
    return put_response


def lambda_handler(event, context):

    #read ticker table
    db_tickers = get_tickers()
    tickers_exchange = [ticker['ticker'] for ticker in db_tickers['Items']]
    try:
        # Get urls
        raw_urls = []
        ticker_list = []
        for ticker in tickers_exchange:
            new_raw_urls, new_ticker_list = search_for_stock_news_urls(ticker)
            raw_urls.append(new_raw_urls)
            ticker_list.append(new_ticker_list)

        flat_ticker_list = [i for flatlist in ticker_list for i in flatlist]
        flat_raw_urls = [i for flatlist in raw_urls for i in flatlist]

        cleaned_urls = strip_unwanted_urls(flat_raw_urls)
        cleaned_urls, cleaned_tickers = match_processed_urls(flat_raw_urls, cleaned_urls, flat_ticker_list)
        titles, sentences, final_urls, final_tickers = scrape_sentences_and_titles(cleaned_urls, cleaned_tickers)
        for i in range(0, len(sentences)):
            put_sentence(final_tickers[i], sentences[i], titles[i], final_urls[i])

    except requests.RequestException as e:
         # Send some context about this error to Lambda Logs
         print(e)
         raise e



    response = {
      'statusCode': 200,
      'body': 'successfully created item!',
      'headers': {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    }
    return response
