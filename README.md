LUMI REVERSE ENGINEER PROCESS (for integration with Home Assistant):
found on the older v2.x.x Home Controllers, there is a port open for MQTT. Those MQTT ports can have little to no security or authentication (no authentication for me)
After triggering a command on a phone that's registered in the app, the MQTT topic yields back:

component/hc-zb/control {"cmd":"set","control_source":{"id":"ios-iPhone-+84981328453-1783242837636-26","previous_control_reqid":"","type":"app"},"objects":[{"data":["zigbee-84:2E:14:FF:FE:88:23:A8-1"],"execution":{"command":"OnOff","params":{"on":true}},"type":"devices"}],"reqid":"ios-iPhone-+84981328453-1783242837636-26","source":"core","timestamp":1783242837870}

(which can be replicated by using this command:)

mosquitto_pub -h 192.168.1.94 -t "component/hc-zb/control" -m '{"cmd":"set","control_source":{"id":"ios-iPhone-+84981328453-1783242837636-26","previous_control_reqid":"","type":"app"},"objects":[{"data":["zigbee-84:2E:14:FF:FE:88:23:A8-1"],"execution":{"command":"OnOff","params":{"on":true}},"type":"devices"}],"reqid":"ios-iPhone-+84981328453-1783242837636-26","source":"core","timestamp":1783242837870}'

from the message, we can decode that (anything else that didn't get mentioned means that it is not important, but it still needs to be there to trick the Home Controller):
"cmd":"set": command type,
"control_source": where the command came from:
	"id": the ID of the session/device, with a structure of: (os)-(device model)-(phone number)-(gibberish number)-(gibberish number, I guess this is the OS version of the device, since the device involved is running iOS 26) 
	"previous_control_reqid": don't know what it means
	"type":"app": indicates that the command came from their app
"objects": the payload of the actual command:
	"data": seems like the internal identifier of the device, with the structure (protocol)-(MAC address)-(endpoint number, in this case, it's a switch that has 3 buttons, and button 2 is mapped at endpoint 3. This gets reflected very well in Zigbee2MQTT.)
	"execution": the command to perform on the device, for this device, it's to turn on the endpoint.
	"reqid": same as "id"
	"source":"core": idk?
	"timestamp": kind of obvious, but I don't know the format
after setting some other commands, it's determined that:
	- id, type, reqid, source, timestamp are NOT checked by the HC (which means it can be blank, but it has to be there because if it isn't there the HC won't run the command)
Lumi does not return devices status in the same topic (component/hc-zb/control), but it returns in the "component/dnet-relay/in/status":

component/dnet-relay/in/status {"cmd":"status","objects":[{"data":[{"devid":"1_zigbee-84:2E:14:FF:FE:88:23:A8-1","hash":"zigbee-84:2E:14:FF:FE:88:23:A8-1","states":{"OnOff":{"on":true}},"status":1,"type":"SWITCH"}],"type":"devices"}],"reqid":"r0aNUSFI8T35GKF","source":"core","timestamp":1783304983889}


