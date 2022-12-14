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

hmi_data = instrument.read_registers(11,9,3)
pressure_in = hmi_data[0] / 10
pressure_out = hmi_data[1] / 10
temperature_out = hmi_data[2] / 10
gas_totalizer = (hmi_data[3]*1000 + hmi_data[4])/10
craddle_number = hmi_data[5]

print(hmi_data)

if(hmi_data[8] == 0):
    mode = "CNG"
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

query_first = 'select first(gas_totalizer) from system where time >= ' + str(unix)
query = client.query(query_first)
first = query['system']['first'][0]

last = gas_totalizer


if(last < first):
    last = last + 99999

delta = last - first

print(delta)

monthly_usage = delta * (1.01325 + pressure_out) / 1.01325 * (273 + 15) / (273 + temperature_out)

# print(monthly_usage)

# format the data as a single measurement for influx
body = [
    {
        "measurement": measurement_name,
        "fields": {
            "gas_totalizer": gas_totalizer
        }
    }
]

# connect to influx
ifclient = InfluxDBClient(ifhost,ifport,ifuser,ifpass,ifdb)

# write the measurement
ifclient.write_points(body)

result = subprocess.Popen(['bash','/home/global/proj-sym/tb-logger.sh', str(pressure_in), str(pressure_out), str(temperature_out), str(craddle_number), mode, str(gas_totalizer), str(monthly_usage), ACCESS_TOKEN], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)