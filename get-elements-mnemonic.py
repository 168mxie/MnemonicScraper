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
import hashlib
from selenium.common.exceptions import ElementClickInterceptedException
load_dotenv()
api_key = os.getenv("API_KEY")
client = OpenAI(
    # This is the default and can be omitted
    api_key=api_key
)


class SeleniumContentScraper:
    def __init__(self, start_url):
        self.start_url = start_url
        self.visited_urls = set()

        # Set up headless Chrome
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        self.driver = webdriver.Chrome(options=options)

    def extract_mnemonic_with_llm(self, main_content_text):

        response = client.responses.create(
            model="gpt-4o",
            instructions=f"""
            This is the html file of a website that contains a mnemonic. Your task is to find:
            - The main term being taught 
            - The definition or defining features of the term
            - The mnemonic used to remember it, which is usually a full sentence with the term and/or definitions in red.

            Respond in this JSON format:
            {{ "term": "...", "definition": "...", "mnemonic": "..." }}""",
        
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

   

    def get_next_page(self):
        
        try:
            next_button = self.driver.find_element(By.CLASS_NAME, 'pt-controls-next')
            if next_button.is_enabled():
                next_button.click()
                time.sleep(1.5)  # wait for content to update
                return True
        except (NoSuchElementException, ElementClickInterceptedException) as e:
            print(f"Next button issue: {e}")
        return False

    def scrape_all_pages(self):
        current_url = self.start_url
        all_data = []
        seen_hashes = set()
        count = 1

        self.driver.get(current_url)
        time.sleep(2)

        while True:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            main_content = soup.find("div", id="mainContent")
            main_html = str(main_content) if main_content else ""
            content_hash = hashlib.md5(main_html.encode('utf-8')).hexdigest()

            if content_hash in seen_hashes:
                print("🔁 Page already seen. Stopping to prevent infinite loop.")
                break

            seen_hashes.add(content_hash)

            # Extract with LLM
            mnemonic_json = self.extract_mnemonic_with_llm(main_html)

            data = {
                'url': self.driver.current_url,
                'mainContent': main_html,
                'concept_and_mnemonic': mnemonic_json
            }

            print(f"✅ Scraped page {count}: {self.driver.current_url}")
            count += 1
            all_data.append(data)
            self.save_to_csv(data)

            if not self.get_next_page():
                print("⛔️ No more next pages.")
                break

        self.driver.quit()
        return all_data

    def save_to_csv(self, data, filename="mammoth_memory_elements.csv"):
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

    
    
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(script_dir, "mammoth_memory_elements.csv")

    if os.path.exists(filename):
        os.remove(filename)

    url_list = [
        #WORKS: "https://mammothmemory.net/memory/remembering-months-and-signs-of-the-zodiac/remembering-months/january.html",
        
        #WORKS: "https://mammothmemory.net/chemistry/atomic-structure/protons/protons.html",
        "https://mammothmemory.net/chemistry/periodic-table/elements-of-the-periodic-table/elements-of-the-periodic-table.html",
        #"https://mammothmemory.net/chemistry/periodic-table/elements-of-the-periodic-table/elements-of-the-periodic-table.html"
    ]

    for start_url in url_list:
        scraper = SeleniumContentScraper(start_url)
        scraper.scrape_all_pages()

if __name__ == "__main__":
    main()
