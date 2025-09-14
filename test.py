from selenium import webdriver
from selenium.webdriver.common.by import By

options = webdriver.ChromeOptions()
# options.add_argument("--headless=new")  # Optional: run headless

driver = webdriver.Chrome(options=options)
driver.get("https://www.google.com")
print(driver.title)
driver.quit()