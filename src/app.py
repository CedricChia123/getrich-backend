from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

symbol_news_dict = {}

def initialize_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-dev-shm-usage')

    return webdriver.Chrome(options=options)

def scrape_headline_news(driver, url):
    driver.get(url)

    # Wait for the headlines to be present on the page
    wait = WebDriverWait(driver, 10)
    headlines_present = EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.Box-sc-1hpkeeg-0.hBnhmi h6.typography__StyledTypography-sc-owin6q-0.fkaXgH'))
    wait.until(headlines_present)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    headline_news = []

    # CSS Selector
    headlines = soup.select('a.Box-sc-1hpkeeg-0.hBnhmi h6.typography__StyledTypography-sc-owin6q-0.fkaXgH')

    for headline in headlines:
        headline_text = headline.get_text().strip()
        headline_news.append(headline_text)

    return headline_news

# Method to search result using ticker symbol. returns dictionary
def search_ticker_symbol(symbol_list):
    url_list = dict()
    for symbol in symbol_list:
        url_list[symbol] = f"https://www.coindesk.com/search?s={symbol}&sort=1"
    return url_list

def store_into_db(driver, url_list, symbol_news_dict):
    for symbol, url in url_list.items():
        headlines = scrape_headline_news(driver, url)

        if headlines:
            symbol_news_dict[symbol] = headlines

if __name__ == "__main__":
    # Top 25
    search_list = ["BTC", "XRP", "USDT", "ETH", "BNB", "USDC", "STETH", "DOGE", "ADA", "SOL", "TRX",
                   "LTC", "MATIC", "DOT", "SHIB", "BCH", "UNI", "WBTC", "AVAX", "XLM", "TON", "DAI", "LINK",
                   "BUSD", "LEO"]
    url_list = search_ticker_symbol(search_list)
    
    driver = initialize_driver()
    store_into_db(driver, url_list, symbol_news_dict)
    # Close the driver after scraping all URLs
    driver.quit()

    # Print the headlines stored in the dictionary and write them to the output file
    with open('./output.txt', 'w') as f:
        for symbol, headlines in symbol_news_dict.items():
            if headlines:
                f.write(f"Headline News for {symbol}:\n")
                for idx, headline in enumerate(headlines, 1):
                    f.write(f"{idx}. {headline}\n")
            else:
                f.write(f"No headlines found for {symbol}.\n")

    print("Headlines have been written to output.txt.")