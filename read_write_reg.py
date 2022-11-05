import minimalmodbus

instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1)

pressure_in = instrument.read_register(registeraddress=1, functioncode=3, number_of_decimals=1)
pressure_out = instrument.read_register(registeraddress=2, functioncode=3, number_of_decimals=1)
temperature_out = instrument.read_register(registeraddress=3, functioncode=3, number_of_decimals=1)
totaliser = instrument.read_register(registeraddress=4, functioncode=3, number_of_decimals=1)
status = instrument.read_register(registeraddress=5, functioncode=3, number_of_decimals=1)

print(pressure_in)
print(pressure_out)
print(temperature_out)
print(totaliser)
print(status)