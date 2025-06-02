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
            data = self.get_name_mnemonics(current_url)

            if data:
                print(f"✅ Scraped page {count}")
                count += 1
                all_data.append(data)
                self.save_to_csv(data)

            current_url = self.get_next_page_url()
            time.sleep(0.5)

        self.driver.quit()
        return all_data

    def save_to_csv(self, data, filename="mammoth_memory_tree_mnemonics.csv"):
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

    
    def get_name_mnemonics(self, url):
        try:
            self.driver.get(url)
            time.sleep(2)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            main_content = soup.find("div", id="mainContent")
            main_text = str(main_content) if main_content else ""
            #print(main_text)
            # Extract mnemonic using LLM
            response = client.responses.create(
                model="gpt-4o",
                instructions= f"""
                This is the HTML content of a webpage that contains mnemonics for trees. These mnemonics are somewhat complex. 
               

                Your task is to extract every tree the mnemonic is about, the defining features of the tree, and the mnemonic that ties them together.
                Respond in this JSON format:
                {{ "concept": "...", "definition": "...", "mnemonic": "..." }}""",
                
                
                input=main_text,
            )
    

            mnemonic_json = response.output_text

            return {
                'url': url,
                'mainContent': str(main_content) if main_content else '',
                'concept_and_mnemonic': mnemonic_json
            }
        except Exception as e:
            print(f"Error loading page {url}: {e}")
            return None
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(script_dir, "mammoth_memory_tree_mnemonics.csv")

    if os.path.exists(filename):
        os.remove(filename)

    url_list_multiple = [
        "https://mammothmemory.net/memory/remembering-distinctive-tree-features/remembering-distinctive-tree-features/ash-tree.html"
    ]
    for start_url in url_list_multiple:
        scraper = SeleniumContentScraper(start_url)
        scraper.scrape_all_pages()



if __name__ == "__main__":
    main()
