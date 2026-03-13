from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
import os

def setup_chrome_driver():
    try:
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)
        
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(service=service, options=options)
        return driver
        
    except Exception as e:
        print(f"Erro ao configurar ChromeDriver: {e}")
        return None