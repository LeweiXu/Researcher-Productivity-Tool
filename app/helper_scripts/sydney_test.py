import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_sydney_repo():
    url = "https://ses.library.usyd.edu.au/"
    
    options = uc.ChromeOptions()
    options.add_argument("--headless")  # remove for visible browser
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = uc.Chrome(version_main=138, options=options)
    
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("Selenium succeeded!")
        print(driver.title)
        print(driver.find_element(By.TAG_NAME, "body").text[:500])
    except Exception as e:
        print(f"Selenium failed: {e}")
    finally:
        driver.quit()

test_sydney_repo()
