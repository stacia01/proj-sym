import paho.mqtt.client as mqtt
import json
import minimalmodbus

for i in range(4):
    port_address = '/dev/ttyUSB' + str(i)
    try:
        instrument = minimalmodbus.Instrument(port=port_address, slaveaddress=1, mode='rtu')
        break
    except:
        continue

THINGSBOARD_HOST = 'thingsboard.cloud'
ACCESS_TOKEN = 'ppxBMJsxsW9MyQmIkDm6'

# We assume that all GPIOs are LOW
switch_state = {'switch': False}


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, rc, *extra_params):
    print('Connected with result code ' + str(rc))
    # Subscribing to receive RPC requests
    client.subscribe('v1/devices/me/rpc/request/+')
    # Sending current GPIO status
    client.publish('v1/devices/me/attributes', get_switch_state(), 1)


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print('Topic: ' + msg.topic + '\nMessage: ' + str(msg.payload))
    # Decode JSON request
    data = json.loads(msg.payload)
    # Check request method
    if data['method'] == 'getValue':
        # Reply with GPIO status
        client.publish(msg.topic.replace('request', 'response'), get_switch_state(), 1)
    elif data['method'] == 'setValue':
        status = data['params']
        # Update GPIO status and reply
        set_switch_state(status)
        client.publish(msg.topic.replace('request', 'response'), get_switch_state(), 1)
        client.publish('v1/devices/me/attributes', get_switch_state(), 1)

def get_switch_state():
    return json.dumps(switch_state)

def set_switch_state(status):
    switch_state['switch'] = status
    if(status):
        instrument.write_register(22,1)
    else:
        instrument.write_register(22,0)

client = mqtt.Client()
# Register connect callback
client.on_connect = on_connect
# Registed publish message callback
client.on_message = on_message
# Set access token
client.username_pw_set(ACCESS_TOKEN)
# Connect to ThingsBoard using default MQTT port and 60 seconds keepalive interval
client.connect(THINGSBOARD_HOST, 1883, 60)

try:
    client.loop_forever()
except KeyboardInterrupt:
    exit