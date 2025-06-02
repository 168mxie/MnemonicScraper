from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
from urllib.parse import urljoin
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()
api_key = os.getenv("API_KEY")
client = OpenAI(
    # This is the default and can be omitted
    api_key=api_key
)

class SeleniumContentScraper:
    def __init__(self, start_url, driver=None):
        self.start_url = start_url
        self.visited_urls = set()

        if driver:
            self.driver = driver  # Reuse shared driver
            self._owns_driver = False
        else:
            # Create a new headless Chrome if no driver is passed
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            self.driver = webdriver.Chrome(options=options)
            self._owns_driver = True

    def close(self):
        if self._owns_driver:
            self.driver.quit()

    def extract_mnemonic_with_llm(self, main_content_text):

        response = client.responses.create(
            model="gpt-4o",
            instructions=f"""
            This is the html file of a website that contains one or multiple mnemonics for remembering words from a different language. For each mnemonic, your task is to find:
            - The main term being taught in the foreign language
            - The definition of the term in English
            - The mnemonic used to remember it, which is usually a full sentence with the term and/or definitions in red.
            - An image to aid in the memory of the mnemonic IF APPLICABLE
            - Key words that rhyme or sound similar to the term which can be used to remember it. These are usually in red. Note that sometimes part of the keyword is highlighted in red, make sure that the keyword is always a full English word

            Respond with a JSON array, where each item is an object with:
                - "term": The term being remembered
                - "definition": The definition of the term
                - "mnemonic": the mnemonic used to remember the term and definition if applicable
                - "image": Link to image source used to remember mnemonic if applicable
                - "keywords": key words that sound similar to the term or definition that are used in the mnemonic if applicable""",
        
            input=main_content_text,
        )
        return response.output_text

        
    
    def get_content(self, url):
        try:
            self.driver.get(url)
            time.sleep(2)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            main_content = soup.find("div", id="mainContent")
            main_text = str(main_content) if main_content else ""
            #print(main_text)
            # Extract mnemonic using LLM
            mnemonic_json = self.extract_mnemonic_with_llm(main_text)

            return {
                'url': url,
                'mainContent': str(main_content) if main_content else '',
                'concept_and_mnemonic': mnemonic_json
            }
        except Exception as e:
            print(f"Error loading page {url}: {e}")
            return None
        

    def get_next_page_url(self):
        try:
            # Look for the 'page-next' div and then find the anchor inside it
            next_div = self.driver.find_element(By.CLASS_NAME, 'page-next')
            next_link = next_div.find_element(By.TAG_NAME, 'a')
            next_url = next_link.get_attribute('href')
            
            if next_url:
                return urljoin(self.driver.current_url, next_url)
        except NoSuchElementException:
            return None

        return None

    def scrape_all_pages(self):
        current_url = self.start_url
        all_data = []
        count = 1

        while current_url and current_url not in self.visited_urls:
            print(f"Scraping: {current_url}")
            self.visited_urls.add(current_url)
            data = self.get_content(current_url)

            if data:
                print(f"✅ Scraped page {count}")
                count += 1
                all_data.append(data)
                self.save_to_csv(data)

            #current_url = self.get_next_page_url()
            time.sleep(0.5)

        return all_data

    def save_to_csv(self, data, filename="mammoth_memory_main_mnemonics.csv"):
        if data:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, filename)
            df = pd.DataFrame([{
                "url": data["url"],
                "concept_and_mnemonic": data["concept_and_mnemonic"]
            }])
            df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
            print(f"📁 Data saved to {file_path}")
        else:
            print("⚠️ No data to save")

def get_div(url):
    try:
        time.sleep(1)  # Small delay for politeness
        response = requests.get(url)
        response.raise_for_status()  # Raise exception if HTTP error
        soup = BeautifulSoup(response.text, 'html.parser')
        main_content = soup.find("div", class_="word-grid")
        main_text = str(main_content) if main_content else ""
        return main_text
    except Exception as e:
        print(f"❌ Error fetching or parsing {url}: {e}")
        return ""  
    
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(script_dir, "mammoth_memory_main_mnemonics.csv")

    # Step 1: Load previously scraped URLs from existing CSV (if it exists)
    already_scraped_urls = set()
    if os.path.exists(filename):
        try:
            df_existing = pd.read_csv(filename)
            already_scraped_urls = set(df_existing["url"].dropna().tolist())
            print(f"🧠 Found {len(already_scraped_urls)} previously scraped URLs.")
        except Exception as e:
            print(f"⚠️ Error reading existing CSV: {e}")


    # url_list = [
    #     "https://mammothmemory.net/memory/remembering-months-and-signs-of-the-zodiac/remembering-months/january.html",    
    #     "https://mammothmemory.net/chemistry/atomic-structure/protons/protons.html",
    #     "https://mammothmemory.net/chemistry/periodic-table/the-history-of-the-periodic-table/the-history-of-the-periodic-table.html",
    #     "https://mammothmemory.net/chemistry/types-of-particle/atoms-1/atoms-1.html",
    #     "https://mammothmemory.net/chemistry/naming-chemicals/elements-ending-in-ium/elements-ending-in-ium.html",
    #     "https://mammothmemory.net/chemistry/chemical-formulae/iron-oxide-rust/iron-oxide-rust.html",
    #     "https://mammothmemory.net/chemistry/chemical-bonding/covalent-bonding-sharing/covalent-bonding-sharing.html",
    #     "https://mammothmemory.net/chemistry/acids-alkalis-bases-and-salts/acids/acids.html",
    #     "https://mammothmemory.net/chemistry/acids-alkalis-bases-and-salts/testing-acids-and-alkalis-using-universal-indicator/testing-acids-and-alkalis-using-universal-indicator.html",
    #     "https://mammothmemory.net/chemistry/hydrocarbons/hydrocarbons-an-introduction/hydrocarbons-an-introduction.html",
    #     "https://mammothmemory.net/chemistry/fractional-distillation/remembering-the-order-of-the-fractions-of-crude-oil/remembering-the-order-of-the-fractions-of-crude-oil.html",
    #     "https://mammothmemory.net/chemistry/electrolysis/what-is-electrolysis/what-is-electrolysis.html",
    #     "https://mammothmemory.net/chemistry/moles/moles-are-a-number/moles-are-a-number.html",
    #     "https://mammothmemory.net/chemistry/laboratory-tests/testing-for-hydrogen/testing-for-hydrogen.html",
    #     "https://mammothmemory.net/chemistry/the-earths-structure/the-structure-of-the-earth/the-structure-of-the-earth.html",
    #     "https://mammothmemory.net/chemistry/dissolving/solvent/solvent.html",
    #     "https://mammothmemory.net/biology/characteristics-and-classifications/taxonomy/taxonomy.html",
    #     "https://mammothmemory.net/biology/characteristics-and-classifications/dichotomous-keys/dichotomous-keys.html",
    #     "https://mammothmemory.net/biology/classification-of-animals/vertebrates/vertebrates.html",
    #     "https://mammothmemory.net/biology/classification-of-animals/invertebrates/invertebrates.html",
    #     "https://mammothmemory.net/biology/classification-of-animals/bony-and-cartilaginous-fish/bony-and-cartilaginous-fish.html",
    #     "https://mammothmemory.net/biology/skeletons-and-bones/skeleton-and-bones/humerus.html",
    #     "https://mammothmemory.net/biology/muscles/muscles/antagonist-muscles.html",
    #     "https://mammothmemory.net/biology/muscles/tendons-ligaments-and-muscles/tendons.html",
    #     "https://mammothmemory.net/biology/plants/classification-of-plants/how-plants-are-categorised.html",
    #     "https://mammothmemory.net/biology/plants/tropism-in-plants/tropism-in-plants.html",
    #     "https://mammothmemory.net/biology/cell-structure-and-organisation/whats-in-a-cell/cells.html",
    #     "https://mammothmemory.net/biology/cell-structure-and-organisation/the-main-parts-of-a-cell/ribosomes.html",
    #     "https://mammothmemory.net/biology/movement-in-and-out-of-cells/osmosis/osmosis.html",
    #     "https://mammothmemory.net/biology/organs-and-systems/the-heart/arteries.html",
    #     "https://mammothmemory.net/biology/respiration/plants/photosynthesis-and-respiration.html",
    #     #"https://mammothmemory.net/biology/nutrition-and-digestion/the-alimentary-canal/alimentary-canal.html",
    #     "https://mammothmemory.net/biology/coordination-and-response/nerves/nerve.html",
    #     "https://mammothmemory.net/biology/organisms-and-their-environment/ecology-and-ecosystems/habitat-place.html",
    #     "https://mammothmemory.net/biology/organisms-and-their-environment/ecology-and-ecosystems/predator-and-prey.html",
    #     "https://mammothmemory.net/biology/variation-and-selection/mutation/mutation.html",
    #     "https://mammothmemory.net/biology/dna-genetics-and-inheritance/gregor-mendel/the-punnet-square.html",
    #     "https://mammothmemory.net/biology/diseases-and-immunity/diseases-and-immunity/diseases-and-immunity.html",
    # ]

    #for start_url in url_list:
    #    if start_url in already_scraped_urls:
    #        print(f"⏩ Skipping already scraped URL: {start_url}")
    #        continue
    #    scraper = SeleniumContentScraper(start_url)
    #    scraper.scrape_all_pages()
    num = 2
    
    visited_urls = set()
    total_urls = []
    
    def find_next_page_link_from_url(url):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise error for bad status
        except requests.RequestException as e:
            print(f"Error fetching page: {e}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        next_div = soup.find('div', class_='page-next')

        if not next_div:
            print("No div with class 'page-next' found.")
            return None

        link = next_div.find('a')
        if link and 'href' in link.attrs:
            base_url = "https://mammothmemory.net/"
            return urljoin(base_url, link['href'])

        print("No link found inside 'page-next' div.")
        return None
    
    for num in range(2, 27):
        current_url = f"https://mammothmemory.net/languages/mandarin-chinese/mandarin-chinese/vocabulary/mandarin-chinese-word-list.html?p={num}&order=alpha"
        html_content = get_div(current_url)

        soup = BeautifulSoup(html_content, "html.parser")

        # Find all <a> tags inside the grid-menu
        links = soup.select(".word-grid a")

        # Extract href attributes and store in a list
        url_lists = [a["href"] for a in links if a.has_attr("href")]

        base_url = "https://mammothmemory.net/languages/mandarin-chinese/mandarin-chinese/vocabulary/"
        full_urls = [urljoin(base_url, url) for url in url_lists]
        total_urls += full_urls
        visited_urls.add(current_url)
        current_url = find_next_page_link_from_url(current_url)
        #print(current_url)
    
    driver = webdriver.Chrome() 
    #print(total_urls)
    #print(full_urls)
    for start_url in total_urls:
        if start_url in already_scraped_urls:
            print(f"⏩ Skipping already scraped URL: {start_url}")
            continue
        scraper = SeleniumContentScraper(start_url, driver=driver)
        scraper.scrape_all_pages()
    driver.quit()
if __name__ == "__main__":
    main()
