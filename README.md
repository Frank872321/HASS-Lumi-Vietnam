# LUMI REVERSE ENGINEER PROCESS (for integration with Home Assistant):
found on the older v2.x.x Home Controllers (HC), there is a port open for MQTT. Those MQTT ports can have little to no security or authentication (no authentication for me)
After triggering a command on a phone that's registered in the app, the MQTT topic yields back:
> component/hc-zb/control {"cmd":"set","control_source":{"id":"[REDACTED]","previous_control_reqid":"","type":"app"},"objects":[{"data":["[REDACTED]"],"execution":{"command":"OnOff","params":{"on":true}},"type":"devices"}],"reqid":"[REDACTED]","source":"core","timestamp":1783242837870}

(which can be replicated by using this command:)

> mosquitto_pub -h (IP of the HC) -t "component/hc-zb/control" -m '{"cmd":"set","control_source":{"id":"[REDACTED]","previous_control_reqid":"","type":"app"},"objects":[{"data":["[REDACTED]"],"execution":{"command":"OnOff","params":{"on":true}},"type":"devices"}],"reqid":"[REDACTED]","source":"core","timestamp":1783242837870}'

from the message, we can decode that (anything else that didn't get mentioned means that it is not important, but it still needs to be there to trick the Home Controller):
- "cmd":"set": command type,
- "control_source": where the command came from:
	- "id": the ID of the session/device, with a structure of: (os)-(device model)-(phone number)-(gibberish number)-(gibberish number, I guess this is the OS version of the device, since the device involved is running iOS 26) 
	- "previous_control_reqid": don't know what it means
	- "type":"app": indicates that the command came from their app
- "objects": the payload of the actual command:
	- "data": seems like the internal identifier of the device, with the structure (protocol)-(MAC address)-(endpoint number)
	- "execution": the command to perform on the device, for this device, it's to turn on the endpoint.
	- "reqid": same as "id"
	- "source":"core": idk?
	- "timestamp": kind of obvious, but I don't know the format
- after setting some other commands, it's determined that:
	- id, type, reqid, source, timestamp are NOT checked by the HC (which means it can be blank, but it has to be there because if it isn't there the HC won't run the command)

Lumi does not return devices status in the same topic (component/hc-zb/control), but it returns in the "component/dnet-relay/in/status":

> component/dnet-relay/in/status {"cmd":"status","objects":[{"data":[{"devid":"1_zigbee-84:2E:14:FF:FE:88:23:A8-1","hash":"zigbee-84:2E:14:FF:FE:88:23:A8-1","states":{"OnOff":{"on":true}},"status":1,"type":"SWITCH"}],"type":"devices"}],"reqid":"r0aNUSFI8T35GKF","source":"core","timestamp":1783304983889}

which accurately reflects the state of the device. 

---
## How does this integration work?
Simply, this integration sends messages into certain MQTT topics hosted by the HC to control the devices that the hub is connected to. Currently, the device only supports switches (due to me being poor causing my inability to buy more Lumi/Zigbee products).

To add support to the integration, you can follow these steps:
1. Connect a Zigbee devices other than switches to the Lumi Home Controller.
2. Connect the MQTT explorer and observe components/hc-zb/control and components/dnet-relay/in/status
3. Open an issue and then paste the changes in

You can also add code to help me :)

---
## How do I use this integration?
You can follow these steps:
1. Download HACS into your Home Assistant system, if you haven't done that
2. Open the HACS menu, click the 3-dot symbol and choose the "Custom repositories" option.
3. Paste in the following:
    - Repository: ```https://github.com/Frank872321/HASS-Lumi-Vietnam```
    - Category: select "Integration"
4. Close the pop-up, you will see the Lumi integration. Install
5. After installing, go into Settings > Devices & Services > Integrations > Add integration
6. Search for the Lumi integration. Once you click on it, a pop-up will appear asking for your IP and Port
7. Type in the HC's IP and MQTT port (Usually 1883)
8. After that, go and interact with your devices via the app or physically. It will appear in the Devices list.
## How do I delete this integration?
It is the same as other custom integrations
## DISCLAIMER
This project is not an official app or service by Lumi Vietnam. This project is made by the community, and by using it, you agree that the author will **not** bear responsibility if any damage happen to your devices.