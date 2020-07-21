# Modbus Server
Script modbus_server.py is an example script that converts data of your rotavapor into a modbus server.

Script is updating holding registers of a modbus server from Rotavapor R-300 API in a loop and sending changes from modbus clients back to API.
Modbus RTU server is currently not working because a bug in pymodbus. This part is still under development.

## CSV mapping
Script modbus_mapping_csv.py is a tool for creating csv file with modbus mapping difined in modbus_server.py.
