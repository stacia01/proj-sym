import minimalmodbus
import subprocess
from influxdb import InfluxDBClient
from influxdb import DataFrameClient
import datetime
import time

current_year = datetime.datetime.now().year
current_month = datetime.datetime.now().month
date_time = datetime.datetime(current_year, current_month, 1, 0, 0, 0)
# print("Given Date:",date_time)
unix = int(time.mktime(date_time.timetuple()) * 1000000000)
print(unix)

ACCESS_TOKEN = 'ppxBMJsxsW9MyQmIkDm6'

for i in range(4):
    port_address = '/dev/ttyUSB' + str(i)
    try:
        instrument = minimalmodbus.Instrument(port=port_address, slaveaddress=1, mode='rtu')
        break
    except:
        continue

hmi_data = instrument.read_registers(11,11,3)
pressure_in = hmi_data[0] / 10
pressure_out = hmi_data[1] / 10
temperature_out = hmi_data[2] / 10
gas_totalizer = (hmi_data[3]*1000 + hmi_data[4])/10
craddle_number = hmi_data[5]
hot_water = hmi_data[10]

print(hmi_data)

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

client = DataFrameClient(host = 'localhost', port = 8086)
client.switch_database('home')

try:
    query_gas_totalizer = 'select last(gas_totalizer) from system'
    query1 = client.query(query_gas_totalizer)
    prev_totalizer = query1['system']['last'][0]
    query_usage  = 'select last(monthly_usage) from system'
    query2 = client.query(query_usage)
    prev_usage = query2['system']['last'][0]

except:
    prev_totalizer = gas_totalizer
    prev_usage = 0

last_totalizer = gas_totalizer


if(last_totalizer < prev_totalizer):
    last_totalizer = last_totalizer + 999999.9

delta = last_totalizer - prev_totalizer

print(delta)

monthly_usage = prev_usage + (delta * (1.01325 + pressure_out) / 1.01325 * (273 + 15) / (273 + temperature_out))

# print(monthly_usage)

# format the data as a single measurement for influx
body = [
    {
        "measurement": measurement_name,
        "fields": {
            "gas_totalizer": gas_totalizer,
            "monthly_usage": monthly_usage
        }
    }
]

# connect to influx
ifclient = InfluxDBClient(ifhost,ifport,ifuser,ifpass,ifdb)

# write the measurement
ifclient.write_points(body)

result = subprocess.Popen(['bash','/home/global/proj-sym/tb-logger.sh', str(pressure_in), str(pressure_out), str(temperature_out), str(craddle_number), mode, str(gas_totalizer), str(monthly_usage), str(hot_water), ACCESS_TOKEN], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)