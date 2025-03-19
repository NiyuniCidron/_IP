import requests
import json
import os
import schedule

def get_public_ip():
    """Retrieves the current public IP address."""
    try:
        response = requests.get("https://api.ipify.org?format=json")
        response.raise_for_status()
        return response.json()["ip"]
    except requests.exceptions.RequestException as e:
        print(f"Error getting public IP: {e}")
        return None

def send_discord_message(webhook_url, current_ip, description):
    """Sends a message to a Discord webhook."""
    data = {
        "embeds": [
            {
                "title": "External IP Checker",
                "description": "New external IP detected"
                               f"```{current_ip}```",
                "color": 0x7b23eb
            }
        ]
    }
    try:
        response = requests.post(webhook_url, json=data)
        response.raise_for_status()
        if response.status_code == 204:
            print(f"Discord message sent to {description} ({webhook_url}) successfully.")
        else:
            print(f"Discord message to {description} ({webhook_url}) failed. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Discord message to {description} ({webhook_url}): {e}")

def main():
    """Checks for IP changes and sends a Discord message if necessary."""

    config_file = "config.json"

    if not os.path.exists(config_file):
        default_config = {
            "webhooks": [
                {"url": "webhook_url1", "description": "Server1 - Channel1"},
                {"url": "webhook_url2", "description": "Server2 - Channel2"}
            ]
        }
        with open(config_file, "w") as f:
            json.dump(default_config, f, indent=4)
        print(f"Created default config.json. Please edit it with your webhook URLs and descriptions.")
        return

    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        webhooks = config.get("webhooks", [])
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading config.json: {e}")
        return

    if not webhooks:
        print("No Discord webhooks configured in config.json.")
        return

    ip_file = "previous_ip.txt"
    previous_ip = None

    if os.path.exists(ip_file):
        with open(ip_file, "r") as f:
            previous_ip = f.read().strip()

    current_ip = get_public_ip()

    if current_ip is None:
        return

    if previous_ip is None or current_ip != previous_ip:
        print(f"IP address changed from {previous_ip} to {current_ip}")

        for webhook in webhooks:
            send_discord_message(webhook["url"], current_ip, webhook["description"])

        with open(ip_file, "w") as f:
            f.write(current_ip)
    else:
        print("IP address has not changed.")

if __name__ == "__main__":
    main()