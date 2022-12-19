import paho.mqtt.client as mqtt
import json
import minimalmodbus
from influxdb import InfluxDBClient
from influxdb import DataFrameClient
import datetime
import time

THINGSBOARD_HOST = 'thingsboard.cloud'
ACCESS_TOKEN = 'kFfsqrlV3ErI23uxOYUT'

switch_state = {'switch': True}

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
        instrument.write_register(22,0)
    else:
        instrument.write_register(22,1)

# Data capture and upload interval in seconds. Less interval will eventually hang the DHT22.
INTERVAL=30

# sensor_data = {'pressure_in': 0, 'pressure_out': 0, 'temperature_out': 0, 'craddle_number': 0, 'mode': "UNDEFINED", 'gas_totalizer': 0, 'monthly_usage': 0, 'hot_water': 0}
sensor_data = {}
next_reading = time.time() 

client = mqtt.Client()

# Register connect callback
client.on_connect = on_connect
# Registed publish message callback
client.on_message = on_message

# Set access token
client.username_pw_set(ACCESS_TOKEN)

# Connect to ThingsBoard using default MQTT port and 60 seconds keepalive interval
client.connect(THINGSBOARD_HOST, 1883, 30)

client.loop_start()

try:
    while True:
        current_month = datetime.datetime.now().month
        
        for i in range(4):
            port_address = '/dev/ttyUSB' + str(i)
            try:
                instrument = minimalmodbus.Instrument(port=port_address, slaveaddress=1, mode='rtu')
                break
            except:
                continue

        hmi_data = instrument.read_registers(11,12,3)
        pressure_in = hmi_data[0] / 10
        pressure_out = hmi_data[1] / 10
        temperature_out = hmi_data[2] / 10
        gas_totalizer = (hmi_data[11]*10000 + hmi_data[3]*1000 + hmi_data[4])/10
        craddle_number = hmi_data[5]
        hot_water = hmi_data[10] / 10

        if(hmi_data[8] == 0):
            mode = "CNG"
            mode_boolean = False
        elif(hmi_data[8] == 1):
            mode = "LPG"
        else:
            mode = "UNDEFINED"

        # influx configuration - edit these
        ifuser = "symgo"
        ifpass = "123456"
        ifdb   = "home"
        ifhost = "127.0.0.1"
        ifport = 8086
        measurement_name = "system"

        query_client = DataFrameClient(host = 'localhost', port = 8086)
        query_client.switch_database('home')

        try:
            query_gas_totalizer = 'select last(gas_totalizer) from system'
            query1 = query_client.query(query_gas_totalizer)
            prev_totalizer = query1['system']['last'][0]
            query_usage  = 'select last(monthly_usage) from system'
            query2 = query_client.query(query_usage)
            prev_usage = query2['system']['last'][0]
            query_month = 'select last(month) from system'
            query3 = query_client.query(query_month)
            prev_month = query3['system']['last'][0]

            if(prev_month != current_month):
                prev_usage = 0

        except:
            prev_totalizer = gas_totalizer
            prev_usage = 0
            prev_month = current_month

        last_totalizer = gas_totalizer


        if(last_totalizer < prev_totalizer):
            last_totalizer = last_totalizer + 999999.9

        delta = last_totalizer - prev_totalizer
        print(delta)

        if(pressure_out < 400 and temperature_out < 200):
            monthly_usage = prev_usage + (delta * (1.01325 + pressure_out) / 1.01325 * (273 + 15) / (273 + temperature_out))
            sensor_data['monthly_usage'] = monthly_usage

            # format the data as a single measurement for influx
            body = [
                {
                    "measurement": measurement_name,
                    "fields": {
                        "gas_totalizer": gas_totalizer,
                        "monthly_usage": monthly_usage,
                        "month": current_month
                    }
                }
            ]

            # connect to influx
            ifclient = InfluxDBClient(ifhost,ifport,ifuser,ifpass,ifdb)

            # write the measurement
            ifclient.write_points(body)

        if(pressure_in < 400):
            sensor_data['pressure_in'] = pressure_in
        if(pressure_out < 400):
            sensor_data['pressure_out'] = pressure_out
        if(temperature_out < 500):
            sensor_data['temperature_out'] = temperature_out
        if(gas_totalizer < 1000000):
            sensor_data['gas_totalizer'] = gas_totalizer
        sensor_data['craddle_number'] = craddle_number
        if(hot_water < 400):
            sensor_data['hot_water'] = hot_water
        sensor_data['mode'] = mode

        # Sending humidity and temperature data to ThingsBoard
        client.publish('v1/devices/me/telemetry', json.dumps(sensor_data), 1)

        next_reading += INTERVAL
        sleep_time = next_reading - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)

except KeyboardInterrupt:
    pass

client.loop_stop()
client.disconnect()
