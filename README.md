Unifi2Ntfy allows you to send alerts from your UniFi controller to Ntfy when your primary internet connection (WAN) is going down.

## Quick Start
Follow these steps to run Unifi2Ntfy. You'll need a docker host, a Ntfy server and a UDM Pro with a trusted certificate running at the default IP:
1. Log in on your UniFi controller. Create a new user with the role Viewer and call it ntfy. 
2. On your docker host, create a new directory and save the following as `docker-compose.yaml` in the new directory. Insert your own passwords and usernames as needed:
```
services:
  unifi2ntfy:
    image: mgaudi/unifi2ntfy:latest
    environment:
      - UNTFY_CONTROLLER_USER="ntfy"
      - UNTFY_CONTROLLER_PW="__CHANGE__secret"
      - UNTFY_NTFY_URL="__CHANGE__http://ntfy.example.com"
      - UNTFY_NTFY_USER="__CHANGE__optional"
      - UNTFY_NTFY_PW="__CHANGE__credentials"
```
3. Run `docker-compose up -d` - Done.
Please check the configuration section below in case something is not working as expected. 

## Description
The tool is polling the UniFi controller every 10s for a new alert about the primary WAN. If it detects a status change (inactive or active), it will push a notification to an Ntfy server. You will need to provide credentials for both your UniFi controller as well as an Ntfy server. 

If you're using a UniFi router for your primary WAN access and have configured a failover / redundant secondary WAN access, you'll get an alert in your UniFi controller's log files. You can send a mail about it as well as receive a push notification on your phone, both of which didn't fit my need for a quick and light-weight dedicated notification about my primary WAN. Unifi2Ntfy specifically covers this scenario.

## Configuration
Use the following settings for more advanced configuration. They need to be set as environment variables for your docker container. 
Parameter | Usage
--- | --- 
UNTFY_DEBUG_MODE | More detailed logging, useful for troubleshooting. *Default: False*
UNTFY_POLLING_INTERVALL | Intervall in seconds for checking the UniFi controller for new alerts. *Default: 10*
UNTFY_PRIMARY_IFACE | The internal interface of your UniFi device. You need to change this if you're not using the default WAN port on a UDM Pro for your primary internet connection. It should be `number of your port - 1`. *Default: eth8*
UNTFY_CONTROLLER_URL | URL of your UniFi controller, without a trailing `/` *Default: https://192.168.1.1*
UNTFY_CONTROLLER_USER | User for your UniFi controller. Warning: Using your regular admin user is a security risk! Instead, set up a dedicated user with the Viewer role in your controller.
UNTFY_CONTROLLER_PW | Password for the UNTFY_CONTROLLER_USER
UNTFY_CONTROLLER_VERIFY_TLS | You can tell Unifi2Ntfy to ignore the certificate of a UniFi controller by setting this to `False`. This might be relevant in case you're using the default self-signed certificate on the controller and haven't trusted it on the machine you run Unifi2Ntfy. Warning: Changing this setting will pose a security risk! Never use this outside a trusted local network. 
UNTFY_CONTROLLER_TYPE | Experimental! In case you're not using a UDM Pro, set this value to `USG` regardless of where your controller is running.[^1] *Default: UDM Pro* 
UNTFY_NTFY_URL | URL to your Ntfy server, e.g. `https://ntfy.example.com`, without a trailing `/`
UNTFY_NTFY_TOPIC | Topic to which the notification should be pushed. *Default: alerts*
UNTFY_NTFY_USER | Optional: User for authentication on the Ntfy server
UNTFY_NTFY_PW | Optional: Password for UNTFY_NTFY_USER

[^1]: The UDM Pro has different API endpoints, therefore getting alerts from a standalone controller or a different router like a USG requires a different configuration. This feature has not been tested for Unifi2Ntfy. See https://ubntwiki.com/products/software/unifi-controller/api for details on the API.

## Copyright & License
- Copyright 2024 Max Frei
- See [LICENSE](LICENSE) for license information