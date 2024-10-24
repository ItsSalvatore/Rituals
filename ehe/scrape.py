from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

# Setup Chrome options to run in headless mode (no UI)
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run Chrome in headless mode
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Set up the WebDriver with Chrome
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # Open the Rituals homepage
    driver.get("https://www.rituals.com/en-nl/home")

    # Allow some time for the page to load fully
    time.sleep(10)  # Adjust the sleep time as necessary to load all dynamic content

    # Get the fully rendered page source
    page_source = driver.page_source

    # Save the HTML to a file in the current directory
    with open("rituals_fully_rendered.html", "w", encoding="utf-8") as file:
        file.write(page_source)

    print("Page successfully saved as 'rituals_fully_rendered.html'")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Close the browser
    driver.quit()
