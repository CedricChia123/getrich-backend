from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime
from dotenv import load_dotenv
import pymongo
import os
import time

load_dotenv()
client = pymongo.MongoClient(os.environ.get("MONGODB_URI")) 
db = client['getrich']
news = db['news']
global_dict = {'BTC': 'bitcoin', 'XRP': 'xrp', 'ETH': 'ethereum', 'BNB': 'bnb', 'DOGE': 'dogecoin', 'ADA': 'cardano', 'SOL': 'solana', 'TRX': 'tron',
               'LTC': 'litecoin', 'MATIC': 'polygon', 'DOT': 'polkadot', 'SHIB': 'shiba-inu', 'BCH': 'bitcoin-cash', 'UNI': 'uniswap', 'AVAX': 'avalanche'}
now = datetime.now()
formatted_date = now.strftime("%b %d, %Y")

def initialize_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--log-level=3')

    return webdriver.Chrome(options=options)

def scrape_headline_news(driver, url):
    headline_selector = 'div.sc-aef7b723-0.dDQUel.news_description--title h5.sc-16891c57-0.fmcNVa.base-text'
    time_selector = 'div.sc-aef7b723-0.dDQUel.news_time span.sc-16891c57-0.dZnbgJ.base-text'
    button_xpath = """/html/body/div[1]/div[2]/div[1]/div[2]/div/div/div[7]/section/div/div[2]/button/div[1]/div"""

    driver.get(url)
    
    time.sleep(2)
    wait = WebDriverWait(driver, 10)
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler'))).click()
    for _ in range(2):
        driver.find_element(By.XPATH, button_xpath).click()
        time.sleep(2)
    headlines_present = EC.presence_of_all_elements_located((By.CSS_SELECTOR, headline_selector))
    time_present = EC.presence_of_element_located((By.CSS_SELECTOR, time_selector))
    wait.until(headlines_present)
    wait.until(time_present)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    headline_news = []

    headlines = soup.select(headline_selector)
    dates = soup.select(time_selector)

    # Assuming the number of headlines and dates is the same
    for i in range(len(headlines)):
        headline_text = headlines[i].get_text().strip()
        date_text = dates[i].get_text().strip()
        # Store the headline and date together as a tuple
        headline_news.append((date_text, headline_text))

    print(headline_news)

    return headline_news

# Method to search result using ticker symbol. returns dictionary
def search_ticker_symbol(symbol_list):
    url_list = dict()
    for symbol in symbol_list:
        # Retrieve the full name of ticker symbol
        name = global_dict[symbol]
        url_list[symbol] = f"https://coinmarketcap.com/currencies/{name}/#News"
    return url_list

def create_data(driver, url_list):
    symbol_news_dict = {}
    for symbol, url in url_list.items():
        headlines = scrape_headline_news(driver, url)

        if headlines:
            symbol_news_dict[symbol] = headlines
        print(f"Completed scraping {symbol}")

    return symbol_news_dict

def store_into_db(data):
    existing_entry = news.find_one({"date": formatted_date})

    if existing_entry:
        symbol_headlines_dict = existing_entry.get("symbol_headlines", {})

        for symbol, headlines in data.items():
            if symbol not in symbol_headlines_dict:
                symbol_headlines_dict[symbol] = []

            for headline in headlines:
                if validate_time(headline[0]) and headline[1] not in [h["headline"] for h in symbol_headlines_dict[symbol]]:
                    symbol_headlines_dict[symbol].append({
                        "headline": headline[1],
                        "created": now,
                        "processed": False
                    })

        news.update_one({"date": formatted_date}, {"$set": {"symbol_headlines": symbol_headlines_dict}})
    else:
        symbol_headlines_dict = {}

        for symbol, headlines in data.items():
            if headlines:
                symbol_headlines_dict[symbol] = []

                for headline in headlines:
                    if validate_time(headline[0]):
                        symbol_headlines_dict[symbol].append({
                            "headline": headline[1],
                            "created": now,
                            "processed": False
                        })

        if symbol_headlines_dict:
            news.insert_one({"symbol_headlines": symbol_headlines_dict, "date": formatted_date})

def validate_time(data):
    if data == 'an hour ago' or 'minutes' in data:
        return True
    return False

if __name__ == "__main__":
    # Top 15
    search_list = ["BTC", "XRP", "ETH", "BNB", "DOGE", "ADA", "SOL", "TRX", "LTC", "MATIC", "DOT", "SHIB", "BCH", "UNI", "AVAX"]
    url_list = search_ticker_symbol(search_list)

    start_time = time.time()
    driver = initialize_driver()
    symbol_news_dict = create_data(driver, url_list)
    # Close the driver after scraping all URLs
    driver.quit()

    store_into_db(symbol_news_dict)

    print("Headlines have been stored in MongoDB.")
    end_time = time.time()
    time_taken = end_time - start_time
    print("Time taken for process is", time_taken, "seconds.")