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
import traceback
from concurrent.futures import ProcessPoolExecutor, wait


load_dotenv()
client = pymongo.MongoClient(os.environ.get("MONGODB_URI")) 
db = client['getrich']
news = db['news']
global_dict = {'BTC': 'bitcoin', 'XRP': 'xrp', 'ETH': 'ethereum', 'BNB': 'bnb', 'DOGE': 'dogecoin', 'ADA': 'cardano', 'SOL': 'solana', 'TRX': 'tron',
               'LTC': 'litecoin', 'MATIC': 'polygon', 'DOT': 'polkadot', 'SHIB': 'shiba-inu', 'BCH': 'bitcoin-cash', 'UNI': 'uniswap', 'AVAX': 'avalanche'}
now = datetime.now()
formatted_date = now.strftime("%b %d, %Y")
search_list = ["BTC", "XRP", "ETH", "BNB", "DOGE", "ADA", "SOL", "TRX", "LTC", "MATIC", "DOT", "SHIB", "BCH", "UNI", "AVAX"]

class Scraper1:
    def __init__(self):
        self.driver = self.initialize_driver()

    def initialize_driver(self):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--log-level=3')

        return webdriver.Chrome(options=options)

    def handle_cookie_consent(self):
        try:
            # Wait for the cookie consent banner to be present
            cookie_banner_present = EC.presence_of_element_located((By.ID, 'onetrust-button-group'))
            WebDriverWait(self.driver, 10).until(cookie_banner_present)

            # Close the cookie consent banner by clicking the "Accept All" button (or any other appropriate button)
            accept_button = self.driver.find_element(By.ID, 'onetrust-accept-btn-handler')
            accept_button.click()

            # Wait briefly to allow the page to update after closing the banner
            time.sleep(2)
        except NoSuchElementException:
            print("Cookie consent banner not found. Proceeding without handling it.")
        except Exception as e:
            print("Moving on")

    def scrape_headline_news(self, url):
        headline_selector = 'div.sc-aef7b723-0.dDQUel.news_description--title h5.sc-16891c57-0.fmcNVa.base-text'
        button_selector = 'button.sc-16891c57-0.foDtUe'
        time_selector = 'div.sc-aef7b723-0.dDQUel.news_time span.sc-16891c57-0.dZnbgJ.base-text'

        self.driver.get(url)
        self.handle_cookie_consent()
        
        wait = WebDriverWait(self.driver, 10)
        headlines_present = EC.presence_of_all_elements_located((By.CSS_SELECTOR, headline_selector))
        see_more_button_present = EC.presence_of_element_located((By.CSS_SELECTOR, button_selector))
        time_present = EC.presence_of_element_located((By.CSS_SELECTOR, time_selector))
        wait.until(headlines_present)
        wait.until(see_more_button_present)
        wait.until(time_present)

        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        headline_news = []

        headlines = soup.select(headline_selector)
        dates = soup.select(time_selector)

        # Assuming the number of headlines and dates is the same
        for i in range(len(headlines)):
            headline_text = headlines[i].get_text().strip()
            date_text = dates[i].get_text().strip()
            # Store the headline and date together as a tuple
            headline_news.append((date_text, headline_text))

        # Click the "See More" button twice to load more news
        for _ in range(2):
            see_more_button = self.driver.find_element(By.CSS_SELECTOR, button_selector)
            see_more_button.click()

            time.sleep(5)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            headlines = soup.select(headline_selector)
            dates = soup.select(time_selector)

            for i in range(len(headlines)):
                headline_text = headlines[i].get_text().strip()
                date_text = dates[i].get_text().strip()
                headline_news.append((date_text, headline_text))

        return headline_news

    # Method to search result using ticker symbol. returns dictionary
    def search_ticker_symbol(self, symbol_list):
        url_list = dict()
        for symbol in symbol_list:
            # Retrieve the full name of ticker symbol
            name = global_dict[symbol]
            url_list[symbol] = f"https://coinmarketcap.com/currencies/{name}/#News"
        return url_list

    def create_data(self, url_list):
        symbol_news_dict = {}
        for symbol, url in url_list.items():
            headlines = self.scrape_headline_news(url)

            if headlines:
                symbol_news_dict[symbol] = headlines
            print(f"Completed scraping {symbol} from coinmarketcap")

        return symbol_news_dict

    def store_into_db(self, data):
        existing_entry = news.find_one({"date": formatted_date})

        if existing_entry:
            symbol_headlines_dict = existing_entry.get("symbol_headlines", {})

            for symbol, headlines in data.items():
                if symbol not in symbol_headlines_dict:
                    symbol_headlines_dict[symbol] = []

                for headline in headlines:
                    if self.validate_time(headline[0]) and headline[1] not in [h["headline"] for h in symbol_headlines_dict[symbol]]:
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
                        if self.validate_time(headline[0]):
                            symbol_headlines_dict[symbol].append({
                                "headline": headline[1],
                                "created": now,
                                "processed": False
                            })

            if symbol_headlines_dict:
                news.insert_one({"symbol_headlines": symbol_headlines_dict, "date": formatted_date})

    def validate_time(self, data):
        if data == 'an hour ago' or 'minutes' in data:
            return True
        return False

def scraper_1():
    scraper = Scraper1()
    try:
        url_list = scraper.search_ticker_symbol(search_list)
        symbol_news_dict = scraper.create_data(url_list)
        scraper.store_into_db(symbol_news_dict)
    except Exception as e:
        print("An exception occurred in scraper_1:")
        print(traceback.format_exc())

class Scraper2:
    def __init__(self):
        self.driver = self.initialize_driver()

    def initialize_driver(self):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--log-level=3')  # Suppress log messages

        return webdriver.Chrome(options=options)

    def scrape_headline_news(self, url):
        self.driver.get(url)

        # Wait for both headlines and dates to be present on the page
        wait = WebDriverWait(self.driver, 10)
        headlines_present = EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.Box-sc-1hpkeeg-0.hBnhmi h6.typography__StyledTypography-sc-owin6q-0.fkaXgH'))
        dates_present = EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.searchstyles__DateWrapper-sc-ci5zlg-24.iQeyNE h6.typography__StyledTypography-sc-owin6q-0.fQGhGk'))
        wait.until(headlines_present)
        wait.until(dates_present)

        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
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
    def search_ticker_symbol(self, symbol_list):
        url_list = dict()
        for symbol in symbol_list:
            url_list[symbol] = f"https://www.coindesk.com/search?s={symbol}&sort=1"
        return url_list

    def create_data(self, url_list):
        symbol_news_dict = {}
        for symbol, url in url_list.items():
            headlines = self.scrape_headline_news(url)

            if headlines:
                symbol_news_dict[symbol] = headlines
            print(f"Completed scraping {symbol} from coindesk")

        return symbol_news_dict

    def store_into_db(self, data):
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

    def validate_time(self, data):
        if data == 'an hour ago' or 'minutes' in data:
            return True
        return False

def scraper_2():
    scraper = Scraper2()
    try:
        url_list = scraper.search_ticker_symbol(search_list)
        symbol_news_dict = scraper.create_data(url_list)
        scraper.store_into_db(symbol_news_dict)
    except Exception as e:
        print("An exception occurred in scraper_2:")
        print(traceback.format_exc())

if __name__ == "__main__":
    start_time = time.time()
    with ProcessPoolExecutor() as executor:
        # Run scraper_1 in one process and scraper_2 in another process
        future_1 = executor.submit(scraper_1)
        future_2 = executor.submit(scraper_2)

        # Wait for both processes to complete
        wait([future_1, future_2])

    print("Both scrapers have finished running.")
    end_time = time.time()
    time_taken = end_time - start_time
    print("Time taken for process is", time_taken, "seconds.")