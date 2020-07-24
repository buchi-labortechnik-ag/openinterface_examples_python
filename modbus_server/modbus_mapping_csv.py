'''
This script is generating csv file with modbus mapping from main script.
All values are stored in holding registers and coded as signed integer.
'''
import modbus_server

with open("modbus_mapping.csv", "w") as f: 
    f.write("holding register,value,multiplier,writable\n")
    for i, item in enumerate(modbus_server.modbus_mapping, 1):
        s = ",".join([str(i), str(item[0]), str(item[3]), 'no' if item[4] else 'yes'])
        print(s)
        f.write(s + "\n")
