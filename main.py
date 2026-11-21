
from pathlib import Path
from hashlib import sha256
from time import sleep, monotonic
from getpass import getpass
import shutil

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ============================================================
# CONFIGURATION
# ============================================================

PDF_FILENAME = "live_mar_charts.pdf"

DOWNLOAD_TIMEOUT = 3600
FILE_STABILITY_SECONDS = 5
POLL_INTERVAL = 1

RETRY_DELAY = 60
NEXT_BACKUP_DELAY = 60

PAGE_WAIT_TIMEOUT = 30

CAREMEDS_URL = (
    "https://cm2.caremeds.co.uk/role_care_provider/home"
)


# ============================================================
# USER INPUT AND VALIDATION
# ============================================================

def get_user_settings():

    print("\n=== e-MAR BACKUP CONFIGURATION ===")

    primary_drive = input(
        "Enter USB flash drive letter: "
    ).strip().rstrip(":").upper()

    redundant_drive = input(
        "Enter redundant drive letter (press Enter to skip): "
    ).strip().rstrip(":").upper()

    download_directory = input(
        "Enter existing download directory: "
    ).strip().strip('"')

    username = input(
        "Caremeds username: "
    ).strip()

    password = getpass(
        "Caremeds password: "
    )

    # Validate drive letters

    if len(primary_drive) != 1 or not primary_drive.isalpha():

        raise ValueError(
            "Invalid primary drive letter."
        )

    if redundant_drive and (
        len(redundant_drive) != 1
        or not redundant_drive.isalpha()
    ):

        raise ValueError(
            "Invalid redundant drive letter."
        )

    if redundant_drive == primary_drive:

        raise ValueError(
            "Primary and redundant drives must be different."
        )

    # Validate download directory

    download_directory = Path(
        download_directory
    ).expanduser().resolve()

    if not download_directory.is_dir():

        raise FileNotFoundError(
            f"Download directory does not exist: "
            f"{download_directory}"
        )

    if not username or not password:

        raise ValueError(
            "Username and password are required."
        )

    return (
        primary_drive,
        redundant_drive,
        download_directory,
        username,
        password
    )


# ============================================================
# DRIVE VALIDATION
# ============================================================

def get_drive_path(letter):

    if not letter:
        return None

    drive_root = Path(f"{letter}:\\")
    destination = drive_root / PDF_FILENAME

    if not drive_root.is_dir():

        raise FileNotFoundError(
            f"Drive {letter}: is unavailable."
        )

    return destination


# ============================================================
# USER-VISIBLE COUNTDOWN
# ============================================================

def countdown(seconds, message):

    for remaining in range(seconds, 0, -1):

        minutes, secs = divmod(remaining, 60)

        print(
            f"\r{message}: {minutes:02d}:{secs:02d}",
            end="",
            flush=True
        )

        sleep(1)

    print(f"\r{message}: Complete!          ")


# ============================================================
# SELENIUM CONFIGURATION
# ============================================================

def create_driver(download_directory):

    options = Options()

    options.add_argument("--no-sandbox")

    # Uncomment for headless operation:
    options.add_argument("--headless=new")

    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(
                download_directory.resolve()
            ),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
    )

    driver = webdriver.Chrome(options=options)

    driver.maximize_window()

    return driver


# ============================================================
# SELENIUM HELPERS
# ============================================================

def click_element(driver, locator):

    element = WebDriverWait(
        driver,
        PAGE_WAIT_TIMEOUT
    ).until(
        EC.element_to_be_clickable(locator)
    )

    element.click()

    return element


# ============================================================
# CAREMEDS LOGIN AND NAVIGATION
# ============================================================

def navigate_to_emar_report(driver, username, password):

    print("\nOpening Caremeds.")

    driver.get(CAREMEDS_URL)

    username_field = WebDriverWait(
        driver,
        PAGE_WAIT_TIMEOUT
    ).until(
        EC.presence_of_element_located(
            (By.ID, "user_username")
        )
    )

    password_field = driver.find_element(
        By.ID,
        "user_password"
    )

    username_field.send_keys(username)

    password_field.send_keys(password)

    password_field.send_keys(Keys.RETURN)

    print("Login submitted.")

    # GDPR cancellation

    click_element(
        driver,
        (By.CSS_SELECTOR, '[data-bb-handler="cancel"]')
    )

    print("Dashboard loaded.")

    # Reports menu

    click_element(
        driver,
        (By.XPATH, '/html/body/nav/div/ul[2]/li')
    )

    # Live e-MAR report

    click_element(
        driver,
        (By.XPATH, '/html/body/nav/div/ul[2]/li/ul/li[5]')
    )

    print("e-MAR report opened.")


# ============================================================
# PDF DOWNLOAD MONITOR
# ============================================================

def wait_for_download(download_directory, timeout=DOWNLOAD_TIMEOUT):

    pdf_path = download_directory / PDF_FILENAME

    partial_file = Path(
        str(pdf_path) + ".crdownload"
    )

    print("\nWaiting for e-MAR PDF download.")

    start_time = monotonic()

    last_size = -1

    stable_since = None

    while True:

        elapsed = int(monotonic() - start_time)

        minutes, seconds = divmod(elapsed, 60)

        print(
            f"\rDownload elapsed: {minutes:02d}:{seconds:02d}",
            end="",
            flush=True
        )

        # Maximum download time

        if elapsed >= timeout:

            raise TimeoutError(
                "PDF download exceeded maximum waiting time."
            )

        # Check PDF exists and Chrome has finished downloading

        if pdf_path.is_file() and not partial_file.exists():

            current_size = pdf_path.stat().st_size

            if current_size > 0 and current_size == last_size:

                if stable_since is None:

                    stable_since = monotonic()

                elif (
                    monotonic() - stable_since
                    >= FILE_STABILITY_SECONDS
                ):

                    print("\nPDF download completed successfully.")

                    return pdf_path

            else:

                last_size = current_size

                stable_since = None

        else:

            last_size = -1

            stable_since = None

        sleep(POLL_INTERVAL)


# ============================================================
# GENERATE AND DOWNLOAD PDF
# ============================================================

def download_emar_pdf(driver, download_directory):

    pdf_path = download_directory / PDF_FILENAME

    partial_file = Path(
        str(pdf_path) + ".crdownload"
    )

    # Remove stale files before starting a new download

    pdf_path.unlink(missing_ok=True)

    partial_file.unlink(missing_ok=True)

    print("\nGenerating e-MAR PDF.")

    click_element(
        driver,
        (By.XPATH, '/html/body/div[4]/div/div/div[3]/button[1]')
    )

    print("\nStarting PDF download.")

    # Retain original Caremeds download behaviour

    download_url = driver.current_url

    driver.get(download_url)

    return wait_for_download(download_directory)


# ============================================================
# FILE INTEGRITY VERIFICATION
# ============================================================

def calculate_checksum(file_path):

    digest = sha256()

    with open(file_path, "rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):

            digest.update(chunk)

    return digest.hexdigest()


def copy_and_verify(source, destination):

    print(f"\nCopying to {destination.parent}.")

    shutil.copy2(source, destination)

    source_checksum = calculate_checksum(source)

    destination_checksum = calculate_checksum(destination)

    if source_checksum != destination_checksum:

        raise IOError(
            f"Checksum verification failed for {destination}."
        )

    print(
        f"Checksum verification successful: {destination}"
    )

    return True


# ============================================================
# BACKUP PROCESS
# ============================================================

def perform_backups(
    pdf_path,
    primary_destination,
    redundant_destination
):

    failures = []

    # ----------------------------------------
    # REDUNDANT BACKUP
    # ----------------------------------------

    if redundant_destination:

        try:

            copy_and_verify(
                pdf_path,
                redundant_destination
            )

            print("Redundant backup successful.")

        except Exception as error:

            failures.append(
                f"Redundant drive: {error}"
            )

            print(
                f"Redundant backup failed: {error}"
            )

    else:

        print("\nRedundant backup skipped.")

    # ----------------------------------------
    # PRIMARY USB BACKUP
    # ----------------------------------------

    try:

        copy_and_verify(
            pdf_path,
            primary_destination
        )

        print("Primary USB backup successful.")

    except Exception as error:

        failures.append(
            f"Primary USB drive: {error}"
        )

        print(
            f"Primary USB backup failed: {error}"
        )

    # ----------------------------------------
    # REPORT FAILURES
    # ----------------------------------------

    if failures:

        raise RuntimeError(
            "One or more backups failed:\n"
            + "\n".join(failures)
        )

    print("\nAll requested backups verified successfully.")


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    (
        primary_drive,
        redundant_drive,
        download_directory,
        username,
        password
    ) = get_user_settings()

    primary_destination = get_drive_path(
        primary_drive
    )

    redundant_destination = get_drive_path(
        redundant_drive
    )

    pdf_path = download_directory / PDF_FILENAME

    # Tracks whether a completed PDF is awaiting backup

    pending_pdf = False

    print("\n========================================")
    print("       e-MAR AUTOMATED BACKUP")
    print("========================================")

    print(f"\nDownload directory: {download_directory}")

    print(f"Primary backup: {primary_drive}:")

    if redundant_drive:

        print(f"Redundant backup: {redundant_drive}:")

    else:

        print("Redundant backup: Disabled")

    while True:

        driver = None

        try:

            print("\nStarting backup iteration.")

            # --------------------------------
            # DOWNLOAD PDF IF REQUIRED
            # --------------------------------

            if not pending_pdf:

                driver = create_driver(
                    download_directory
                )

                navigate_to_emar_report(
                    driver,
                    username,
                    password
                )

                pdf_path = download_emar_pdf(
                    driver,
                    download_directory
                )

                pending_pdf = True

                print("\nPDF ready for backup.")

                # Close browser before copying

                driver.quit()

                driver = None

            else:

                print(
                    "\nReusing previously downloaded PDF "
                    "after an earlier backup failure."
                )

            # --------------------------------
            # CHECK SOURCE FILE
            # --------------------------------

            if (
                not pdf_path.is_file()
                or pdf_path.stat().st_size == 0
            ):

                raise FileNotFoundError(
                    "Downloaded PDF is missing or empty."
                )

            # --------------------------------
            # BACKUP AND VERIFY
            # --------------------------------

            perform_backups(
                pdf_path,
                primary_destination,
                redundant_destination
            )

            # --------------------------------
            # SUCCESS
            # --------------------------------

            print("\n========================================")
            print("       BACKUP SUCCESSFUL")
            print("========================================")

            # Delete only after successful verification

            countdown(
                10,
                "Preparing temporary file cleanup"
            )

            pdf_path.unlink()

            pending_pdf = False

            print("Temporary PDF deleted.")

            # --------------------------------
            # NEXT ITERATION
            # --------------------------------

            countdown(
                NEXT_BACKUP_DELAY,
                "Time until next backup"
            )

        except Exception as error:

            print("\n========================================")
            print("       BACKUP ERROR")
            print("========================================")

            print(f"Error: {error}")

            # --------------------------------
            # CLOSE CHROME SAFELY
            # --------------------------------

            if driver is not None:

                try:

                    driver.quit()

                except Exception as cleanup_error:

                    print(
                        f"Browser cleanup error: {cleanup_error}"
                    )

                driver = None

            # --------------------------------
            # PRESERVE COMPLETED PDF
            # --------------------------------

            if pending_pdf and pdf_path.is_file():

                print(
                    "\nDownloaded PDF preserved for retry."
                )

            else:

                pending_pdf = False

                print(
                    "\nA new download will be attempted "
                    "on the next iteration."
                )

            # --------------------------------
            # RETRY
            # --------------------------------

            print("\nRetrying backup process.")

            countdown(
                RETRY_DELAY,
                "Time until retry"
            )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print("\nBackup program stopped by user.")

    except Exception as error:

        print(f"\nProgram could not start: {error}")