import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# List of university repo URLs to test
urls = {
    "University of Melbourne": "https://fbe.unimelb.edu.au/about/academic-staff",
    "Australian National University": "https://openresearch-repository.anu.edu.au/",
    "University of Sydney": "https://ses.library.usyd.edu.au/",
    "University of Queensland": "https://espace.library.uq.edu.au/",
    "University of New South Wales": "https://unsworks.unsw.edu.au/",
    "Monash University": "https://bridges.monash.edu/",
    "University of Western Australia": "https://research-repository.uwa.edu.au/",
    "University of Adelaide": "https://digital.library.adelaide.edu.au/home",
}

def test_with_bs4(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Heuristic: check if the page has a <title> and at least some content in body
            title = soup.title.string if soup.title else "No title"
            body_text = soup.body.get_text(strip=True) if soup.body else ""
            if body_text and len(body_text) > 100:
                return True, title
            else:
                return False, "Body content too short or empty"
        else:
            return False, f"HTTP status {response.status_code}"
    except Exception as e:
        return False, str(e)

import undetected_chromedriver as uc
# ...existing code...

def test_with_selenium(url):
    options = uc.ChromeOptions()
    # Do NOT use headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,800")
    # Set a common user agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    # Set language
    options.add_argument("--lang=en-US,en")


    driver = driver = uc.Chrome(version_main=138, options=options)

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        # Simulate human-like delay
        import time, random
        time.sleep(random.uniform(1.5, 3.0))
        body_text = driver.find_element(By.TAG_NAME, "body").text
        title = driver.title
        if title == "Just a moment...":
            return False, "Page requires interaction (e.g., Cloudflare protection)"
        elif body_text and len(body_text) > 100:
            return True, title
        else:
            print(body_text)
            return False, "Body content too short or empty"
    except Exception as e:
        return False, str(e)

def main():
    print(f"{'University':35} | {'BS4 Success':10} | {'Selenium Success':15} | Details")
    print("-" * 90)
    for uni, url in urls.items():
        bs4_success, bs4_detail = test_with_bs4(url)
        selenium_success, selenium_detail = test_with_selenium(url)
        print(f"{uni:35} | {str(bs4_success):10} | {str(selenium_success):15} | BS4: {bs4_detail} | Selenium: {selenium_detail}")

if __name__ == "__main__":
    main()