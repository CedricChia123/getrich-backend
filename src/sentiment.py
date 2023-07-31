# Processes the result to feed into FinGPT
from dotenv import load_dotenv
import pymongo
import os
from datetime import datetime

load_dotenv()
client = pymongo.MongoClient(os.environ.get("MONGODB_URI")) 
db = client['getrich']
news = db['news']

now = datetime.now()
formatted_date = now.strftime("%b %d, %Y")

def load_data():
    data = news.find_one({"date": formatted_date})
    print(data)
    return data

def calculate_sentiment(data):
    coin_to_headlines = data['symbol_headlines']
    score_list = dict()
    for symbol in coin_to_headlines:
        headlines = coin_to_headlines[symbol]
        score = 0
        for headline in headlines:
            # Call FinGPT, placebo function first
            print(headline['headline'])
            score += score
        score_list[symbol] = score
    return score_list

if __name__ == "__main__":
    data = load_data()
    result = calculate_sentiment(data)
    print(result)