import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

import pandas as pd

def extract(cap:float=float("inf")):
    print("initializing driver...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)

    link = "https://ccrps.org/clinical-research-blog/top-50-clinical-research-organizations-cros-worldwide-complete-2025-directory"
    driver.get(link)
    print("driver initialized")
    time.sleep(2)
    
    table = driver.find_element(By.CSS_SELECTOR, ".dataframe")
    i = 0
    targets = []
    for row in table.find_elements(By.CSS_SELECTOR, "tbody > tr"):
        if i >= cap:
            break
        name,_,specialization,_,notable_client = row.find_elements(By.TAG_NAME, "td")
        targets.append((i,name.text, specialization.text, notable_client.text))
        i+=1
    
    df = pd.DataFrame(targets).rename({1:"name", 2: "specialization", 3:"notable_client", 0:"index"}, axis=1).drop("index", axis=1)
    df.to_csv("data/targets.csv", index=False)

    driver.quit()
