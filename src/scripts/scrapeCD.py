from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from dotenv import load_dotenv
import pymongo
import os
import time

load_dotenv()
client = pymongo.MongoClient(os.environ.get("MONGODB_URI")) 
db = client['getrich']
news = db['news']

now = datetime.now()
formatted_date = now.strftime("%b %d, %Y")

def initialize_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-dev-shm-usage')

    return webdriver.Chrome(options=options)

def scrape_headline_news(driver, url):
    driver.get(url)

    # Wait for both headlines and dates to be present on the page
    wait = WebDriverWait(driver, 10)
    headlines_present = EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.Box-sc-1hpkeeg-0.hBnhmi h6.typography__StyledTypography-sc-owin6q-0.fkaXgH'))
    dates_present = EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.searchstyles__DateWrapper-sc-ci5zlg-24.iQeyNE h6.typography__StyledTypography-sc-owin6q-0.fQGhGk'))
    wait.until(headlines_present)
    wait.until(dates_present)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    headline_news = []

    # CSS Selectors for headlines and dates
    headlines = soup.select('a.Box-sc-1hpkeeg-0.hBnhmi h6.typography__StyledTypography-sc-owin6q-0.fkaXgH')
    dates = soup.select('div.searchstyles__DateWrapper-sc-ci5zlg-24.iQeyNE h6.typography__StyledTypography-sc-owin6q-0.fQGhGk')

    # Assuming the number of headlines and dates is the same
    for i in range(len(headlines)):
        headline_text = headlines[i].get_text().strip()
        date_text = dates[i].get_text().strip()
        # Store the headline and date together as a tuple
        headline_news.append((date_text, headline_text))

    return headline_news

# Method to search result using ticker symbol. returns dictionary
def search_ticker_symbol(symbol_list):
    url_list = dict()
    for symbol in symbol_list:
        url_list[symbol] = f"https://www.coindesk.com/search?s={symbol}&sort=1"
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
                if headline[0] == formatted_date and headline[1] not in [h["headline"] for h in symbol_headlines_dict[symbol]]:
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
                    if headline[0] == formatted_date:
                        symbol_headlines_dict[symbol].append({
                            "headline": headline[1],
                            "created": now,
                            "processed": False
                        })

        if symbol_headlines_dict:
            news.insert_one({"symbol_headlines": symbol_headlines_dict, "date": formatted_date})


if __name__ == "__main__":
    search_list = ["BTC", "XRP", "ETH", "BNB", "DOGE", "ADA", "SOL", "TRX",
                   "LTC", "MATIC", "DOT", "SHIB", "BCH", "UNI", "AVAX"]
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