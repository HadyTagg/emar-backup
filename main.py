from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import os
import time
import shutil
import subprocess

flash_drive_dir_letter = input("Enter drive directory letter for the USB Flash Drive: ")
redundant_drive_dir_letter = input("Enter drive directory for the redundant backup drive: ")

caremeds_username = input("Please enter the username for Caremeds: ")
caremeds_password = input("Please enter the password for Caremeds: ")

while True:
    try:
        print("Starting e-MAR backup.")
        standard_operation_delay = 1
        #download_delay = 1800
        download_delay = 1000
        download_dir = "\Downloads"
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--headless=new")
        options.add_experimental_option('prefs', {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
                                        )
        driver = webdriver.Chrome(options=options)
        driver.maximize_window()

        pcs_url = "https://cm2.caremeds.co.uk/role_care_provider/home"
        driver.get(pcs_url)

        time.sleep(standard_operation_delay)
        element_username = driver.find_element(By.ID, "user_username")
        element_password = driver.find_element(By.ID, "user_password")
        element_username.send_keys(caremeds_username)
        element_password.send_keys(caremeds_password)
        element_password.send_keys(Keys.RETURN)

        time.sleep(standard_operation_delay)

        #gdpr_cancel_element = driver.find_element(By.CSS_SELECTOR, '[data-bb-handler="cancel"]')
        #gdpr_cancel_element.click()

        time.sleep(standard_operation_delay)

        reports_button_element = driver.find_element(By.XPATH, '/html/body/nav/div/ul[2]/li')
        reports_button_element.click()

        live_emar_report_button_element = driver.find_element(By.XPATH, '/html/body/nav/div/ul[2]/li/ul/li[5]')
        live_emar_report_button_element.click()

        time.sleep(10)

        print_button_element = driver.find_element(By.XPATH, '/html/body/div[4]/div/div/div[3]/button[1]')
        print_button_element.click()

        print("Waiting for the file to generate and download.")

        time.sleep(download_delay)

        download_url = driver.current_url
        driver.get(download_url)

        print("File download complete. Beginning copying process.")

        time.sleep(10)

        shutil.copy("live_mar_charts.pdf", f"{redundant_drive_dir_letter}:/live_mar_charts.pdf")
        shutil.copy("live_mar_charts.pdf", f"{flash_drive_dir_letter}:/live_mar_charts.pdf")

        print("e-MAR back up complete.")

        time.sleep(10)

        print("Deleting temporary file.")

        if os.path.isfile("live_mar_charts.pdf"):
            os.remove("live_mar_charts.pdf")
            print("File deleted.")
        else:
            print("Backup file does not exist.")

        subprocess.call("TASKKILL /f  /IM  CHROME.EXE")
        subprocess.call("TASKKILL /f  /IM  CHROMEDRIVER.EXE")

        #time.sleep(5367)
        time.sleep(60)
    except:
        print("I have encountered an exception. Retrying.")

        if os.path.isfile("live_mar_charts.pdf"):
            os.remove("live_mar_charts.pdf")
            print("File deleted.")
        else:
            print("Backup file does not exist.")

        subprocess.call("TASKKILL /f  /IM  CHROME.EXE")
        subprocess.call("TASKKILL /f  /IM  CHROMEDRIVER.EXE")

        continue