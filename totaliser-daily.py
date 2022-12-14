import subprocess
from influxdb import DataFrameClient
import datetime
import time

date_time = datetime.datetime(2022, 6, 3, 12, 0, 50)
print("Given Date:",date_time)
unix = int(time.mktime(date_time.timetuple()) * 1000000000)

ACCESS_TOKEN = 'ppxBMJsxsW9MyQmIkDm6'

client = DataFrameClient(host = 'localhost', port = 8086)
client.switch_database('home')

query_first = 'select first(gas_totalizer) from system where time >= ' + str(unix)
first = client.query(query_first)
print(first['system']['first'][0])

query_last = 'select last(gas_totalizer) from system where time >= ' + str(unix)
last = client.query(query_last)
print(last['system']['last'][0])

if(last < first):
    last = last + 99999

delta = last - first

monthly_usage = delta * (1.01325 + 1) / 1.01325 * (273 + 15) / (273 + 30)
# result = subprocess.Popen(['bash','/home/global/proj-sym/log-totaliser.sh', str(monthly_usage), ACCESS_TOKEN], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
