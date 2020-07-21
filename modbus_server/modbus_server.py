#!/usr/bin/env python
"""
Rotavapor R-300 to Modbus Server convertor
--------------------------------------------------------------------------

This is an example of Rotavapor R-300 API to a modbus server converter.
Script is updating holding registers of a modbus server from Rotavapor R-300 API in a loop and sending commands from modbus clients back to API.

Modbus RTU server is not working currently because a bug in pymodbus. This pat is still under development. 
"""

import requests
import csv
from datetime import datetime
import urllib3
from os import path
import numpy as np
import time
import json
from jsonpath_ng import jsonpath, parse
from pymodbus.server.asynchronous import StartTcpServer, StartSerialServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSparseDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer, ModbusAsciiFramer
from multiprocessing import Queue
from threading import Thread

# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #

api_user = 'rw'
api_password = 'tvPj2YZC'
api_url = f"https://109.202.196.94:55055/api/v1"
api_loop_time = 1               # loop duration in seconds

modbus_type = 'TCP'             # 'TCP' or 'RTU'
# TCP config
modbus_ip = 'localhost'
modbus_tcpport = 5020
# RTU config
modbus_port='COM1'			#/dev/ttyp0
modbus_baudrate=9600
modbus_parity='N'     		# (E)ven, (O)dd, (N)one
#modbus_timeout=.005

# --------------------------------------------------------------------------- #
# configure the service logging
# --------------------------------------------------------------------------- #
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)
#log.setLevel(logging.CRITICAL)

auth = (api_user, api_password)

# --------------------------------------------------------------------------- #
# modbus mapping config
# --------------------------------------------------------------------------- #
# 
# - Value name (user ddefined)
# - a lambda for transforming data
# - a jsonpath expression for selecting a value
# - a multiplier: mbodbus_value = int(api_value * multiplier)
# - readonly item - changes in registers in this rows arent send to api

modbus_mapping = np.array([
        ["communication", lambda value: 0x0000, None, 1, True],
        ["heating.set", None, '$.heating.set', 10, False],
        ["heating.act", None, '$.heating.act', 10, True],
        ["heating.running", None, '$.heating.running', 1, False],
        ["---", lambda value: 0x7FFF, None, 1, False],
        ["cooling.set", None, '$.cooling.set', 10, False],
        ["cooling.act", None, '$.cooling.act', 10, True],
        ["cooling.running", None, '$.cooling.running', 1, False],
        ["---", lambda value: 0x7FFF, None, 1, False],
        ["vacuum.set", None, '$.vacuum.set', 10, False],
        ["vacuum.act", None, '$.vacuum.act', 10, True],
        ["vacuum.aerateValveOpen", None, '$.vacuum.aerateValveOpen', 1, False],
        ["vacuum.aerateValvePulse", None, '$.vacuum.aerateValvePulse', 1, False],
        ["vacuum.vacuumValveOpen", None, '$.vacuum.vacuumValveOpen', 1, True],
        ["vacuum.vaporTemp", None, '$.vacuum.vaporTemp', 10, True],
        ["vacuum.autoDestIn", None, '$.vacuum.autoDestIn', 10, True],
        ["vacuum.autoDestOut", None, '$.vacuum.autoDestOut', 10, True],
        ["vacuum.powerPercentAct", None, '$.vacuum.powerPercentAct', 1, True],
        ["---", lambda value: 0x7FFF, None, 1, False],
        ["rotation.set", None, '$.rotation.set', 10, False],
        ["rotation.act", None, '$.rotation.act', 10, True],
        ["rotation.running", None, '$.rotation.running', 1, False],
        ["---", lambda value: 0x7FFF, None, 1, False],
        ["lift.set", None, '$.lift.set', 1, False],
        ["lift.act", None, '$.lift.act', 1, True],
        ["lift.limit", None, '$.lift.limit', 1, False],
        ["---", lambda value: 0x7FFF, None, 1, False],
        ["program.type", lambda value: ['Manual','Timer','Solvent','Method','AutoDest','CloudDest','Dry','Calibration','TightnessTest'].index(value), '$.program.type', 1, True],                   # string
        ["program.set", None, '$.program.set', 1, False],
        ["program.remaining", None, '$.program.remaining', 1, False],
        #["program.solventName", None, '$.program.solventName', 1, False],    # string
        #["program.methodName", None, '$.program.methodName', 1, False],      # string
        #["program.mode", None, '$.program.mode', 1, False],                    # string
        ["program.flaskSize", None, '$.program.flaskSize', 1, False],
        ["---", lambda value: 0x7FFF, None, 1, False],
        #["globalStatus.timeStamp", None, '$.globalStatus.timeStamp', 1, True],
        ["globalStatus.processTime", None, '$.globalStatus.processTime', 1, True],
        ["globalStatus.runId", None, '$.globalStatus.runId', 1, True],
        ["globalStatus.onHold", None, '$.globalStatus.onHold', 1, False],
        ["globalStatus.foamActive", None, '$.globalStatus.foamActive', 1, True],
        ["globalStatus.currentError", None, '$.globalStatus.currentError', 1, True],
        ["globalStatus.running", None, '$.globalStatus.running', 1, False],
        ["globalStatus.timeStamp - year", lambda value: datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z").year, '$.globalStatus.timeStamp', 1, True],
        ["globalStatus.timeStamp - month", lambda value: datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z").month, '$.globalStatus.timeStamp', 1, True],
        ["globalStatus.timeStamp - day", lambda value: datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z").day, '$.globalStatus.timeStamp', 1, True],
        ["globalStatus.timeStamp - hour", lambda value: datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z").hour, '$.globalStatus.timeStamp', 1, True],
        ["globalStatus.timeStamp - minute", lambda value: datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z").minute, '$.globalStatus.timeStamp', 1, True],
        ["globalStatus.timeStamp - second", lambda value: datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z").second, '$.globalStatus.timeStamp', 1, True]       
    ])

missing_value = 0x8000   # placeholder for json values not defined in json
cnt = len(modbus_mapping)     # count of holding registers


# --------------------------------------------------------------------------- #
# API to Modbus part
# --------------------------------------------------------------------------- #

def get_value(json_data, m):

    try:
        value = None
        if m[2] is not None:
            jsonpath_expression = parse(m[2])
            value = jsonpath_expression.find(json_data)[0].value
        if m[1] is not None:
            return round(m[1](value) * m[3]) & 0xFFFF
        else:
            return round(value * m[3]) & 0xFFFF if value is not None else missing_value & 0xFFFF
    except:
        return missing_value & 0xFFFF
        
        
def read_api():
    """ A worker process that runs every so often and
    updates live values of the context.
	
    :param arguments: The input arguments to the call
    """
        
    process_endpoint = api_url + "/process"

    # configure http client session
    with requests.Session() as s:
        s.auth = auth
        s.verify = False
        urllib3.disable_warnings()
            
        # wait for start
        started_at = datetime.now()
        poll_at = datetime.now()

        # read process data
        r = s.get(process_endpoint)
        if r.status_code != 200:
            raise Exception("Unexpected status code when polling process data", r.status_code)
        d = r.json()
        
        return [get_value(d, m) for m in modbus_mapping]
    

def updating_writer(context):
    """ A worker process that runs every so often and
    updates live values of the context.
	
    :param arguments: The input arguments to the call
    """
    while True:
        log.debug("updating the context")
        register = 3
        slave_id = 0x00
        address = 0x00
        try:
            values = read_api()
            log.debug("new values: " + str(values))
            context[slave_id].setValues(register, address, values)
            log.debug(context[slave_id].getValues(register, 0x00, count=cnt))
        except:
            val = min(context[slave_id].getValues(register, 0x00, count=1)[0] + 1, 0x7FFF)   # add +1 of holding register 1
            context[slave_id].setValues(register, address, [val])
            pass
        time.sleep(api_loop_time)


# --------------------------------------------------------------------------- #
# Modbus to API part
# --------------------------------------------------------------------------- #

class CallbackDataBlock(ModbusSparseDataBlock):
    """ A datablock that stores the new value in memory
    and passes the operation to a message queue for further
    processing.
    """

    def __init__(self, registers, queue):
        self.registers = registers
        self.queue = queue
        values = {k: 0 for k in registers.keys()}
        values[0xbeef] = len(values)  # the number of registers
        super(CallbackDataBlock, self).__init__(values)

    def setValues(self, address, value):
        """ Sets the requested values of the datastore
        :param address: The starting address
        :param values: The new values to be set
        """
        super(CallbackDataBlock, self).setValues(address, value)
        self.queue.put((self.registers.get(address, None), address, value))

def rescale_value(value, index):
    """ Value calculaton from unsigned integer to signed integer and
    calculate value with decimal offset

    :param value: The input value to scale
    :param index: Number of holding register
    :returns: The rescaled value
    """
    if value > 0x7FFF:
        value = value - 0x10000
    value = value / modbus_mapping[index-1][3]
    return value

def write_api(value, index):
    """ Method for writing new moddbus value to api

    :param value: The input value to write
    :param index: Number of holding register
    """
    
    mb = modbus_mapping[index-1]    # get row from modbus_mapping (modbus address 1 = mapping_modbus[0])
    if mb[4]: return                # skip readonly value
    jsonp = mb[2][2:].split('.')    # remove '$.' from json path
    js = {jsonp[0] : {jsonp[1] : value}}    
    process_endpoint = api_url + "/process"
    # configure http client session
    with requests.Session() as s:
        s = requests.Session()
        s.auth = auth
        s.verify = False
        urllib3.disable_warnings()
        r = s.put(process_endpoint, json=js)
        if r.status_code != 200:
            raise Exception("Unexpected status code when trying to send message to api", r.status_code)
          
def read_device_map():
    # A helper method for preparing modbus mapping
    registers = {}
    for i in range(1, cnt+1):
        registers[i] = 'api'
    return registers

def device_writer(queue):
    """ A worker process that processes new messages
    from a queue to write to device outputs

    :param queue: The queue to get new messages from
    """
    while True:
        device, address, value = queue.get()
        scaled = rescale_value(value[0], address)
        if len(value) < cnt:
            log.debug("Write(%s) = %s, addres = %s" % (device, value, address))
            log.debug("%s %s" % (modbus_mapping[address-1][0] ,scaled))
            try:
                write_api(scaled, address)
            except:
                log.debug("Error: Is not possible to write to api")
        #if not device: continue
		
# --------------------------------------------------------------------------- #
# main function
# --------------------------------------------------------------------------- #
def run_modbus_server():
    # initialize your data store
    queue = Queue()
    devices = read_device_map()
    block = CallbackDataBlock(devices, queue)
    store = ModbusSlaveContext(di=block, co=block, hr=block, ir=block)
    context = ModbusServerContext(slaves=store, single=True)

    # initialize the server information
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'BUCHI Labortechnik AG'
    identity.ProductCode = 'R-300'
    identity.VendorUrl = 'https://www.buchi.com/'
    identity.ProductName = 'Rotavapor R-300'
    identity.ModelName = 'Rotavapor Modbus Server'
    identity.MajorMinorRevision = '1.0.0.0'

    # run updating thread
    t1 = Thread(target=updating_writer, args=(context,))
    t1.start()
    
    # run writing thread
    t2 = Thread(target=device_writer, args=(queue,))
    t2.start()
    
    # run modbus server
    if modbus_type == 'TCP':
        StartTcpServer(context, identity=identity, address=(modbus_ip, modbus_tcpport))
    elif modbus_type == 'RTU':
		# this part doesn't work because bug in pzmodbus, more info: https://github.com/riptideio/pymodbus/issues/514
        StartSerialServer(context, framer=ModbusRtuFramer, identity=identity, port=modbus_port, baudrate=modbus_baudrate, parity=modbus_parity)

if __name__ == "__main__":
    run_modbus_server()
