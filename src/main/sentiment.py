# Processes the result to feed into FinGPT
from dotenv import load_dotenv
import pymongo
import os
from datetime import datetime

load_dotenv()
client = pymongo.MongoClient(os.environ.get("MONGODB_URI")) 
db = client['getrich']
news = db['news']
sentiments = db['sentiments']

now = datetime.now()
formatted_date = now.strftime("%b %d, %Y")
formatted_date_time = now.strftime("%Y-%m-%d %H:%M:%S")

def load_data():
    data = news.find_one({"date": formatted_date})
    return data

def calculate_sentiment(data):
    coin_to_headlines = data['symbol_headlines']
    score_list = dict()
    for symbol in coin_to_headlines:
        headlines = coin_to_headlines[symbol]
        score = 0
        for headline in headlines:
            if not headline['processed']:
                # Call FinGPT, placebo function first
                print(headline['headline'])
                score += 1
                # Update the 'processed' field to True for the current headline
                news.update_one(
                    {"date": formatted_date, "symbol_headlines." + symbol: {"$elemMatch": {"headline": headline['headline']}}},
                    {"$set": {"symbol_headlines." + symbol + ".$.processed": True}}
                )
        score_list[symbol] = score
    sorted_score_list = dict(sorted(score_list.items(), key=lambda item: item[1], reverse=True))
    return sorted_score_list

def store_into_db(data):
    sentiments.insert_one({'created': formatted_date_time, 'sentiments': data})
    print('Sentiments successfully stored')

if __name__ == "__main__":
    data = load_data()
    result = calculate_sentiment(data)
    store_into_db(result)