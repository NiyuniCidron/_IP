import requests
import os
import schedule
import logging
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global variable to track script state
ip_retrieved = False
last_check_time = None

def get_public_ip():
    """Retrieves the current public IP address with retry logic and fallback APIs."""
    apis = [
        "https://api.ipify.org?format=json",
        "https://ifconfig.me/ip",
        "https://icanhazip.com/"
    ]
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    for i, api in enumerate(apis):
        try:
            if "format=json" in api:
                response = session.get(api)
                response.raise_for_status()
                ip = response.json()["ip"]
            else:
                response = session.get(api)
                response.raise_for_status()
                ip = response.text.strip()

            logging.info(f"Successfully retrieved public IP address from {api}.")
            return ip
        except requests.exceptions.RequestException as e:
            logging.warning(f"Failed to retrieve IP from {api}: {e}")
            if i < len(apis) - 1:
                logging.info(f"Retrying with next API.")
            else:
                logging.error(f"Failed to retrieve public IP from all APIs. Error: {e}")
                send_error_discord_message(f"Failed to retrieve public IP from all APIs. Error: {e}")
    return None

def get_webhooks():
    """Retrieves webhooks from environment variables."""
    webhooks_str = os.environ.get("DISCORD_WEBHOOKS")
    if not webhooks_str:
        logging.error("DISCORD_WEBHOOKS environment variable is not set.")
        return []

    webhooks = []
    for url in webhooks_str.split(","):
        url = url.strip()
        webhooks.append({"url": url}) #only add the url.
    return webhooks

def send_discord_message(webhook_url, current_ip):
    """Sends a message to a Discord webhook."""
    data = {
        "embeds": [
            {
                "title": "External IP Checker",
                "description": f"New external IP detected: ```{current_ip}```",
                "color": 0x7b23eb
            }
        ]
    }
    try:
        response = requests.post(webhook_url, json=data)
        response.raise_for_status()
        if response.status_code == 204:
            logging.info(f"Discord message sent to {webhook_url} successfully.")
        else:
            logging.warning(f"Discord message to {webhook_url} failed. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending Discord message to {webhook_url}: {e}")

def send_error_discord_message(error_message):
    """Sends a Discord message for errors."""
    webhooks = get_webhooks()
    if not webhooks:
        logging.warning("No Discord webhooks configured in environment variables. Cannot send error message.")
        return

    data = {
        "embeds": [
            {
                "title": "External IP Checker - ERROR",
                "description": error_message,
                "color": 0xff0000  # Red color for errors
            }
        ]
    }
    for webhook in webhooks:
        try:
            response = requests.post(webhook["url"], json=data)
            response.raise_for_status()
            if response.status_code == 204:
                logging.info(f"Error message sent to {webhook['url']} successfully.")
            else:
                logging.warning(f"Error message to {webhook['url']} failed. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending error message to {webhook['url']}: {e}")

def check_ip():
    """Checks for IP changes and sends a Discord message if necessary."""
    global ip_retrieved, last_check_time
    webhooks = get_webhooks()

    if not webhooks:
        logging.warning("No Discord webhooks configured in environment variables.")
        return

    ip_file = "/app/data/previous_ip.txt"
    previous_ip = None

    if os.path.exists(ip_file):
        with open(ip_file, "r") as f:
            previous_ip = f.read().strip()

    current_ip = get_public_ip()

    if current_ip is None:
        return

    if previous_ip is None or current_ip != previous_ip:
        logging.info(f"IP address changed from {previous_ip} to {current_ip}")

        for webhook in webhooks:
            send_discord_message(webhook["url"], current_ip) #remove description.

        with open(ip_file, "w") as f:
            f.write(current_ip)
    else:
        logging.info("IP address has not changed.")

    if current_ip:
        ip_retrieved = True
        last_check_time = time.time()

def main():
    """Sets up the scheduler and runs the IP check."""
    interval = int(os.environ.get("CHECK_INTERVAL", 1))
    interval_unit = os.environ.get("CHECK_INTERVAL_UNIT", "minutes").lower()

    # Run check_ip() immediately on startup
    logging.info("Running initial IP check...")
    check_ip()

    if interval_unit == "seconds":
        schedule.every(interval).seconds.do(check_ip)
    elif interval_unit == "minutes":
        schedule.every(interval).minutes.do(check_ip)
    elif interval_unit == "hours":
        schedule.every(interval).hours.do(check_ip)
    elif interval_unit == "days":
        schedule.every(interval).days.do(check_ip)
    else:
        logging.error("Invalid interval unit in environment variable.")
        return

    logging.info(f"Checking IP every {interval} {interval_unit}.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except Exception as e:
        logging.critical(f"Scheduler error: {e}")
        send_error_discord_message(f"Scheduler error: {e}")

if __name__ == "__main__":
    main()