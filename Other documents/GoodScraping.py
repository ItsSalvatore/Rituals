from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import pandas as pd
import psycopg2
from concurrent.futures import ThreadPoolExecutor

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920x1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

print("Chrome browser is gestart!")

women_perfumes_url = "https://www.rituals.com/en-nl/beauty/perfumes/perfume-for-women"
men_perfumes_url = "https://www.rituals.com/en-nl/beauty/perfumes/perfume-for-men"

data = []

def collect_product_urls_with_gender(category_url, gender):
    product_urls = set()
    try:
        driver.get(category_url)
        time.sleep(random.uniform(5, 8))

        while True:
            try:
                show_more_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'js-grid-load-more')]"))
                )
                driver.execute_script("arguments[0].click();", show_more_button)
                time.sleep(random.uniform(3, 5))
            except (NoSuchElementException, TimeoutException):
                break

        product_elements = driver.find_elements(By.CSS_SELECTOR, ".product-tile a[href]")
        product_urls.update([(element.get_attribute("href"), gender) for element in product_elements])

    except WebDriverException as e:
        print(f"Error loading category page {category_url}: {e}")

    return list(product_urls)

def scrape_ingredients_with_gender(url, gender):
    try:
        for attempt in range(3): 
            try:
                driver.get(url)
                time.sleep(random.uniform(5, 8)) 
                break
            except WebDriverException as e:
                print(f"Error opening URL {url}, attempt {attempt + 1}/3: {e}")
                if attempt == 2:
                    raise

        #Produt name
        try:
            product_name = driver.find_element(By.XPATH, "//h1").text.strip()
            print(f"Product name found: {product_name}")
        except NoSuchElementException:
            print(f"Product name not found for product: {url}")
            return 
        
        #Product_standard_price
        try:
            product_standard_price_element = driver.find_element(By.XPATH, "//p[@class='css-16n8scj']")
            product_standard_price = product_standard_price_element.text
            print(f"Product price found: {product_standard_price} for {product_name}")
        except NoSuchElementException:
            print(f"Product price not found for product: {url}")
            return 
        
        #Description
        try:
            description = driver.find_element(By.XPATH, "//h2[@class='css-bm0yvx']")
            description = description.text
            print(f"description found: {description} for {product_name}")
        except NoSuchElementException:
            print(f"h2 element not found for product: {url}")
            return 

        notes = []
        ingredients = []

        # Notes section
        try:
            notes_section = driver.find_element(By.XPATH, "//div[@data-testid='fragrance-notes-wrapper']")
            notes_elements = notes_section.find_elements(By.TAG_NAME, "h4")
            notes = [note.text.strip() for note in notes_elements]
        except NoSuchElementException:
            print(f"No notes section found for {url}")

        # Collection name
        try:
            collection_name_element = driver.find_element(By.XPATH, "//span[@class='css-235sr0']")
            collection_name = collection_name_element.text.strip()
        except NoSuchElementException:
            collection_name = "No Collection"

        # Stock status
        stock_status = "Unknown stock status"  # Default waarde
        try:
            add_to_cart_button = driver.find_elements(By.XPATH, "//div[contains(@class, 'css-1vgfwic')]")
            
            if add_to_cart_button:
                stock_status = "In stock"
            else:
                stock_status = "Out of stock"
        
        except NoSuchElementException:
            print(f"No stock availability section found for {url}")

        #Product details button
        try:
            product_details_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Product Details']"))
            )
            driver.execute_script("arguments[0].click();", product_details_button)
            time.sleep(2)
        except (NoSuchElementException, TimeoutException):
            print(f"No 'Product Details' button found for product: {url}")

        # Ingredients section
        try:
            ingredients_section = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h4[text()='Ingredients']/following-sibling::div"))
            )
            try:
                show_more_button = ingredients_section.find_element(By.XPATH, ".//a[contains(@title, 'Show more')]")
                driver.execute_script("arguments[0].click();", show_more_button)
                time.sleep(2)
                print(f"'Show More' button clicked for product: {url}")
            except NoSuchElementException:
                print(f"No 'Show More' button found for ingredients section in product: {url}")
            
            ingredients_text = ingredients_section.text.strip()
            if "See WARNING" in ingredients_text:
                print(f"'See WARNING' found for product: {url}")
                ingredients_text = ""
            if ingredients_text:
                ingredients = [ing.strip() for ing in ingredients_text.split(",")]
        except (NoSuchElementException, TimeoutException):
            print(f"No ingredients section found for {url}")

        #Package sizes
        try:
            package_size_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'css-1hzsklp')]"))
            )
            driver.execute_script("arguments[0].click();", package_size_button)
            time.sleep(2)  # Wacht totdat de sectie zichtbaar is
        except (NoSuchElementException, TimeoutException):
            print(f"No 'Package Size' button found for product: {url}")

        #Package sizes
        try:
            size_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'css-h5ggfg')]//div[contains(@class, 'css-10qpkiz')]")
            
            sizes = []
            size_number = 1  
            
            for element in size_elements:
                size_text = element.find_element(By.XPATH, ".//span").text
                sizes.append((size_number, size_text))
                size_number += 1 
            
            print(f"Available sizes for product {url}: {sizes}")

            #Import in dataset
            for size_number, size in sizes:
                data.append({
                    "product_name": product_name,
                    "collection_name": collection_name,
                    "description": description,
                    "gender": gender,
                    "product_standard_price": product_standard_price,
                    "stock_status": stock_status,
                    "ingredient": "",
                    "ingredient_number": "",
                    "size": size,
                    "size_number": size_number,
                    "note": "",
                    "note_number": ""
                })

        except NoSuchElementException:
            print(f"No size information found for product: {url}")

        #Import in dataset
        if notes or ingredients:
            for idx, note in enumerate(notes):
                data.append({
                    "product_name": product_name,
                    "collection_name": collection_name,
                    "description": description,
                    "gender": gender,
                    "product_standard_price": product_standard_price,
                    "stock_status": stock_status,
                    "ingredient": "",
                    "ingredient_number": "",
                    "size": "",
                    "size_number": "",
                    "note": note,
                    "note_number": len(notes) - idx
                })

            #Import in dataset
            for idx, ingredient in enumerate(ingredients):
                data.append({
                    "product_name": product_name,
                    "collection_name": collection_name,
                    "description": description,
                    "gender": gender,
                    "product_standard_price": product_standard_price,
                    "stock_status": stock_status,
                    "ingredient": ingredient,
                    "ingredient_number": len(ingredients) - idx,
                    "size": "",
                    "size_number": "",
                    "note": "",
                    "note_number": ""
                })
        else:
            print(f"No ingredients found for product: {url}, skipping.")

    except WebDriverException as e:
        print(f"Error processing URL: {url}, error: {e}")

product_urls_women = collect_product_urls_with_gender(women_perfumes_url, "Women")
product_urls_men = collect_product_urls_with_gender(men_perfumes_url, "Men")

all_product_urls = product_urls_women + product_urls_men

for product_url, gender in all_product_urls:
    scrape_ingredients_with_gender(product_url, gender)

driver.quit()

df = pd.DataFrame(data)
excel_filename = f"test2.xlsx"
df.to_excel(excel_filename, index=False)

print(f"Scraping complete. Data saved to '{excel_filename}'")
