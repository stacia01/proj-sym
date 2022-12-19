import minimalmodbus

for i in range(4):
    port_address = '/dev/ttyUSB' + str(i)
    try:
        instrument = minimalmodbus.Instrument(port=port_address, slaveaddress=1, mode='rtu')
        break
    except:
        continue

instrument.write_register(22,0)