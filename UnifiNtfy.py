"""
Application Unifi2Ntfy 
This tool connects to a UniFi controller and scans for the primary WAN to go inactive or active. In such case,
a notification is sent to an Ntfy server. Note this is a hobby project and not intended for production. 
Use at your own risk!
"""

import os
import time
import sys
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
import json
import logging
import urllib3

class UnifiController:
    """Connection to the UniFi Controller"""
    def __init__(self, 
                 controller_url, 
                 controller_user, 
                 controller_password, 
                 controller_verify_tls, 
                 controller_is_udm_pro):
        self.base_url = controller_url
        self.user = controller_user
        self.password = controller_password
        self.verify_tls = controller_verify_tls
        self.is_udm_pro = controller_is_udm_pro
        if not self.verify_tls:
            logging.warning("Running with unverified TLS. DO NOT use outside trusted networks!")
            urllib3.disable_warnings()

    def auth(self):
        self.session = requests.Session()
        auth_data = {
            "username": self.user,
            "password": self.password
        }
        logging.debug("Auth request for %s", auth_data["username"])
        # see https://ubntwiki.com/products/software/unifi-controller/api
        if self.is_udm_pro:
            url = self.base_url + "/api/auth/login"
        else: 
            url = self.base_url + "/api/login"
        
        headers = {'Content-Type' : 'application/json'}
        try:
            if not self.verify_tls:
                resp = self.session.post(url, data = json.dumps(auth_data), headers=headers, verify=False)
            else:
                resp = self.session.post(url, data = json.dumps(auth_data), headers=headers)
            successful = resp.status_code == 200
            if successful:
                logging.info("Authenticated at Unifi Controller")
            else:
                logging.error("Could not authenticate at Unifi Controller! HTTP error code %s", resp.status_code)
            return(successful)
        except Exception as E:
            logging.exception(E)
            return(False)

    def get_alerts(self):
        if self.is_udm_pro:
            url = self.base_url + "/proxy/network" + "/api/s/default/stat/alarm"
        else: 
            url = self.base_url + "/api/s/default/stat/alarm"
        
        try:
            if not self.verify_tls:
                 resp = self.session.get(url, verify=False)
            else:
                resp = self.session.get(url)
            successful = resp.status_code==200 
            if not successful:
                logging.error("Could not read alerts on Unifi Controller! HTTP error code %s", resp.status_code)
            return(resp.json(), successful)
        except Exception as E:
            logging.exception(E)
            return("", False)

class NtfyService:
    """Connection to the Ntfy server"""
    def __init__(self, ntfy_base_url, ntfy_topic, ntfy_user, ntfy_password):
        self.url = "{}/{}".format(ntfy_base_url, ntfy_topic)
        if ntfy_user and ntfy_password:
            self.auth = HTTPBasicAuth(ntfy_user, ntfy_password)

    def post_notification(self, state):
        retry_counter = 3
        headers = {'X-Title' : 'Unifi WAN', 'X-Tags' : 'orange_circle'}
        text="Primary WAN went DOWN"
        if state == "active":
            headers["X-Priority"] = "2"
            headers["X-Tags"] = "green_circle"
            text="Primary WAN was restored"

        resp = requests.post(url=self.url, data=text, headers=headers, auth=self.auth)
        if resp.status_code != 200:
            if resp.status_code >= 500:
                while retry_counter > 0:
                    logging.debug("Server error - retrying %s more times", retry_counter)
                    retry_counter -= 1
                    resp = requests.post(url=self.url, data=text, headers=headers, auth=self.auth) 
                    if resp.status_code == 200:
                        return
                    time.sleep(2)
                logging.error("Could not send notification! Is the Ntfy server offline?")
            else:
                logging.error("Could not send notification! HTTP error code %s", resp.status_code)

class UnifiNtfy:
    """Unifi2Ntfy application"""
    def __init__(self):
        config = self.load_configuration()
        self.polling_intervall = config["polling_intervall"]
        self.main_iface = config["main_iface"]
        
        logging_level = logging.DEBUG if config["debug_mode"] else logging.INFO
        logging.basicConfig(
            format='%(asctime)s - Unifi2Ntfy - %(levelname)s : %(message)s', 
            datefmt='%Y-%m-%d %H:%M:%S',
            level=logging_level
        )
        logging.info("Starting Unifi2Ntfy ***")
        startup_time = time.time() * 1000
        self.last_known_state = {
            "time": startup_time,
            "state": "active"
        }
        
        self.uicontroller = UnifiController(
            controller_url=config["controller"]["url"],
            controller_user=config["controller"]["user"],
            controller_password=config["controller"]["password"], 
            controller_verify_tls=config["controller"]["verify_tls"],
            controller_is_udm_pro=config["controller"]["is_udm_pro"]
        )
        
        self.ntfy = NtfyService(
            ntfy_base_url=config["ntfy"]["base_url"],
            ntfy_topic=config["ntfy"]["topic"],
            ntfy_user=config["ntfy"]["user"],
            ntfy_password=config["ntfy"]["password"]
        )
    
    def load_configuration(self):
        config = {}
        config["polling_intervall"] = int(os.getenv("UNTFY_POLLING_INTERVALL", 10))
        config["main_iface"] = os.getenv("UNTFY_PRIMARY_IFACE", "eth8")
        config["debug_mode"] = os.getenv("UNTFY_DEBUG_MODE", "False") == "True"

        config["controller"] = {}
        config["controller"]["url"] = os.getenv("UNTFY_CONTROLLER_URL", "https://192.168.1.1")
        config["controller"]["user"] = os.getenv("UNTFY_CONTROLLER_USER", "")
        config["controller"]["password"] = os.getenv("UNTFY_CONTROLLER_PW", "")    
        config["controller"]["verify_tls"] = os.getenv("UNTFY_CONTROLLER_VERIFY_TLS", "True") == "True"
        config["controller"]["is_udm_pro"] = os.getenv("UNTFY_CONTROLLER_TYPE", "UDM Pro") == "UDM Pro"

        config["ntfy"] = {}
        config["ntfy"]["base_url"] = os.getenv("UNTFY_NTFY_URL", "")
        config["ntfy"]["topic"] = os.getenv("UNTFY_NTFY_TOPIC", "alerts")
        config["ntfy"]["user"] = os.getenv("UNTFY_NTFY_USER", "")
        config["ntfy"]["password"] = os.getenv("UNTFY_NTFY_PW", "")
        return config

    def run_loop(self):
        self.running = self.uicontroller.auth()
        while self.running:
            time.sleep(self.polling_intervall)
              
            alerts_response = self.uicontroller.get_alerts()
            if not alerts_response[1]:
                self.uicontroller.auth()
                continue

            alerts = alerts_response[0]["data"]
            for alert in alerts:
                if alert["key"] == "EVT_GW_WANTransition" and alert["iface"] == self.main_iface:
                    if alert["time"] <= self.last_known_state["time"]:
                        break

                    dt = datetime.fromtimestamp(alert["time"] / 1000)
                    logging.info("Primary WAN went %s at %s", alert["state"], dt)
                    if alert["state"] != self.last_known_state["state"]:
                        self.ntfy.post_notification(state=alert["state"])

                    self.last_known_state["time"] = alert["time"]
                    self.last_known_state["state"] = alert["state"]
        sys.exit("Unifi2Ntfy terminated unexpectedly")


def main():
    """Main entry point"""
    app = UnifiNtfy()
    app.run_loop()

if __name__ == "__main__":
    main()