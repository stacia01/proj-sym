import minimalmodbus

instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 9)

temperature = instrument.read_register(registeraddress=7, functioncode=3)
print(temperature)

# instrument.write_register(registeraddress=8, value=int(100), functioncode=6)

# print(instrument.read_register(registeraddress=8, functioncode=3))