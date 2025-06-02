import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import time
import os

class MnemonicScraper:
    def __init__(self, start_url):
        self.start_url = start_url
        self.visited_urls = set()

    def get_page(self, url):
        try:
            response = requests.get(url)
            return response.text
        except requests.RequestException as e:
            print(f"Error getting page: {e}")
            return None

    # Go to next page in list
    def get_next_page_url(self, soup, current_url):
        next_div = soup.find('div', class_='page-next')
        if next_div and next_div.find('a'):
            next_url = next_div.find('a')['href']
            return urljoin(current_url, next_url)
        return None

    def get_mnemonic(self, url):
        content = self.get_page(url)
        if not content:
            return None

        soup = BeautifulSoup(content, 'html.parser')
        word = None
        definition = None
        
        # Assume word/concept is the first h1 tag
        h1_tag = soup.find('h1')
        if h1_tag:
            h1_text = h1_tag.text.strip().replace('\xa0', ' ')
            
            # Assume – or - seperates word from definition if in first h1 tag
            if "–" in h1_text:  
                word, definition = h1_text.split(" – ", 1)
            elif "-" in h1_text: 
                word, definition = h1_text.split(" - ", 1)
            else:
                # Otherwise, take next tag
                word = h1_tag.text.strip()
                if h1_tag.find_next_sibling():
                    definition = h1_tag.find_next_sibling().text.strip()

        # Look only at main content
        main_content = soup.find("div", id="mainContent")
        if main_content == None:
            return None
            
        last_img = None
        found_after_img = False  

        mnemonics = []
        highlighted_text = []
        mnemonic_set = set()
        images = []

         # Iterate through all tags
        for tag in main_content.find_all():  
            if tag.name == "img":
                src = tag.get('src')
                if src:
                    full_url = urljoin(url, src)
                    images.append(full_url)

                # Since maybe multiple mnemonics per page, reset after each image - assume multiple images with red text means multiple mnemonics
                last_img = tag 
                found_after_img = False  

            # red text is marker for mnemonic
            elif tag.name in ["p", "figcaption"] and not found_after_img:
                red_text = tag.find_all(lambda el: el.name == "span" and (
                    "style" in el.attrs and "#ff0000" in el["style"].replace(" ", "").lower()
                ))

                # Sometimes black text interspersed within red text span - remove it
                if red_text:
                    for e in red_text:
                        nested_black_span = e.find(lambda el: el.name == "span" and (
                            "style" in el.attrs and "#000000" in el["style"].replace(" ", "").lower()))

                        if not nested_black_span:
                            if "NOTE" not in e.text.strip():  
                                highlighted_text.append(e.text.strip())

                if red_text and tag not in mnemonic_set and "NOTE" not in tag.text.strip():
                    mnemonic_set.add(tag)
                    mnemonics.append(tag.text.strip())
                    if last_img:
                        found_after_img = True  

        return {
            'url': url,
            'word': word,
            'definition': definition,
            'mnemonic': mnemonics,
            'highlighted_text': highlighted_text,
            'images': images
        }

    def scrape_all_pages(self):
        current_url = self.start_url
        all_data = []

        while current_url and current_url not in self.visited_urls:
            print(f"Scraping: {current_url}")
            self.visited_urls.add(current_url)
            
            content = self.get_page(current_url)
            if not content:
                break

            soup = BeautifulSoup(content, 'html.parser')
            data = self.get_mnemonic(current_url)
            
            if data:
                all_data.append(data)
                self.save_to_csv(data)

            current_url = self.get_next_page_url(soup, current_url)
            
            time.sleep(0.2)

        return all_data

    def save_to_csv(self, data, filename="mammoth_memory_auto_data.csv"):
        if data:
            df = pd.DataFrame([data])
            df.to_csv(filename, mode='a', header=not pd.io.common.file_exists(filename), index=False)
            print(f"Data appended to {filename}")
        else:
            print("No data to save")

def main():
    filename = "mammoth_memory_auto_data.csv"
    if os.path.exists(filename):
            os.remove(filename)
    url_list = [
                "https://mammothmemory.net/memory/remembering-months-and-signs-of-the-zodiac/remembering-signs-of-the-zodiac/capricorn.html",
                "https://mammothmemory.net/chemistry/atomic-structure/protons/protons.html",
                "https://mammothmemory.net/music/music-vocabulary/common-sheet-music-terms/accelerando.html",
                "https://mammothmemory.net/geography/world/europe/what-are-the-european-capital-cities/i/albania.html",
                "https://mammothmemory.net/chemistry/chemical-formulae/iron-oxide-rust/iron-oxide-rust.html"
          
    ]
    
    for start_url in url_list:
        scraper = MnemonicScraper(start_url)
        scraper.scrape_all_pages()

if __name__ == "__main__":
    main()