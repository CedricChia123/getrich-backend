# Processes the result to feed into FinGPT
from dotenv import load_dotenv
import pymongo
import os
from datetime import datetime
import openai
import time

load_dotenv()
client = pymongo.MongoClient(os.environ.get("MONGODB_URI")) 
db = client['getrich']
news = db['news']
sentiments = db['sentiments']
openai.api_key=os.environ.get("OPEN_AI_KEY")

now = datetime.now()
formatted_date = now.strftime("%b %d, %Y")
formatted_date_time = now.strftime("%Y-%m-%d %H:%M:%S")

def load_data():
    data = news.find_one({"date": formatted_date})
    return data

#ChatGPT API
def chat_with_gpt(prompt):
    response=openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[
            {"role":"system", "content":"Hello"},
            {"role": "user","content":prompt}
        ]
    )
    return response.choices[0].message.content.strip()

def calculate_sentiment(data):
    coin_to_headlines = data['symbol_headlines']
    score_list = dict()
    for symbol in coin_to_headlines:
        headlines = coin_to_headlines[symbol]
        score = 0
        for headline in headlines:
            labelled = 0
            if not headline['processed']:
                # Call FinGPT, placebo function first
                process_input=f"Human: Determine the sentiment of the financial news as negative, neutral or positive for {symbol}: {headline['headline']} Assistant: "
                time.sleep(1)
                response=chat_with_gpt(process_input)
                if "negative" in response:
                    score -= 1
                    labelled = -1
                elif "positive" in response:
                    score += 1
                    labelled = 1
                print(f"{headline['headline']} labelled as {labelled}")
                news.update_one(
                    {"date": formatted_date, "symbol_headlines." + symbol: {"$elemMatch": {"headline": headline['headline']}}},
                    {"$set": {"symbol_headlines." + symbol + ".$.processed": True, "symbol_headlines." + symbol + ".$.labelled": labelled}}
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