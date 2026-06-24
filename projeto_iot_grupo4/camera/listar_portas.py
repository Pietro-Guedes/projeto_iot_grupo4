import serial.tools.list_ports

for porta in serial.tools.list_ports.comports():
    print(porta.device, "-", porta.description)