#! /usr/bin/env python3

import requests
import csv
import argparse
import getpass
from datetime import datetime
from datetime import timedelta
import urllib3
from os import path
from os import getcwd
import numpy as np
import time
import json
from jsonpath_ng import jsonpath, parse

# csv mapping config
# - Header title
# - a lambda for transforming data
# - a jsonpath expression for selecting a value
csv_mapping = np.array([
        ["Time s", lambda occured_at, roti_data, roti_value: int(round(occured_at.total_seconds(),0)), None],
        ["PressureAct mbar", None, '$.vacuum.act'],
        ["PressureSet", None, '$.vacuum.set'],
        ["BathAct", None, '$.heating.act'],
        ["BathSet", None, '$.heating.set'],
        ["ChillerAct", None, '$.cooling.act'],
        ["ChillerSet", None, '$.cooling.set'],
        ["Rotation rpm", None, '$.rotation.act'],
        ["Vapor", None, '$.vacuum.vaporTemp'],
        ["AutoDestIn", None, '$.vacuum.autoDestIn'],
        ["AutoDestOut", None, '$.vacuum.autoDestOut'],
        ["AutoDestDiff", lambda occured_at, roti_data, roti_value: round(roti_data['vacuum']['autoDestOut'] - roti_data['vacuum']['autoDestIn'], 2), None],
        ["LiftAct", None, '$.lift.act'],
        ["LiftEnd", None, '$.lift.limit'],
        ["Hold", None, '$.globalStatus.onHold'],
        ["Foam control", None, '$.globalStatus.foamActive'],
        ["PumpAct[0.1%]", None, '$.vacuum.powerPercentAct'],
        ["VacOpen", None, '$.vacuum.vacuumValveOpen']
    ])
csv_dialect = csv.excel # see https://docs.python.org/3/library/csv.html#dialects-and-formatting-parameters
timestamp_after_csvheader = "%d.%m.%Y %H:%M" # set this to None if you don't wan't this second header line
missing_value_char = '*' #set this to None for an empty cell

def build_filepath(folder, device_name, started_at):
    started_at_str = started_at.strftime("%Y-%m-%dT%H%M%S-%f")
    filename = f"{device_name}-{started_at_str}.csv"
    return path.join(folder, filename)

def get_value(occured_at, roti_data, transform, jsonp):
    try:
        roti_value = None
        if jsonp is not None:
            jsonpath_expression = parse(jsonp)
            roti_value = jsonpath_expression.find(roti_data)[0].value
        if transform is not None:
            return transform(occured_at, roti_data, roti_value)
        else:
            return roti_value if roti_value is not None else missing_value_char
    except:
        return missing_value_char

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Remotely logs rotavapor process data into a CSV file. The format is the same as the I-300pro writes to its SD card.')

    parser.add_argument('host', metavar='host', type=str, help='host or IP of rotavapor')
    parser.add_argument('-u', '--user', type=str, help='device password', default='rw')
    parser.add_argument('-p', '--password', type=str, help='device password', required=False)
    parser.add_argument('-f', '--folder', type=str, help='destination folder for the csv files', default=getcwd())
    parser.add_argument('-c', '--cert', type=str, help="root cert file", default="root_cert.crt")

    args = parser.parse_args()

    # ask for password if it wasn't passed in as command line argument
    if args.password is None:
        args.password = getpass.getpass()

    auth = (args.user, args.password)
    base_url = f"https://{args.host}/api/v1"
    info_endpoint = base_url + "/info"
    process_endpoint = base_url + "/process"
    rootcert = "root_cert.crt"

    # configure http client session
    session = requests.Session()
    session.auth = auth
    if path.isfile(rootcert):
        session.verify = rootcert
    else:
        print("Root certificate missing. Disabling certiicate checks...")
        session.verify = False
        urllib3.disable_warnings()

    # verify that this is a Rotavapor
    info_resp = session.get(info_endpoint)
    if info_resp.status_code != 200:
        raise Exception("Unexpected status code when getting device info", info_resp.status_code)
    info_msg = info_resp.json()
    system_name = info_msg["systemName"]
    print(f"Connected to {system_name}")
    if info_msg["systemClass"] != "Rotavapor":
        raise Exception(f"This is not a Rotavapor")
        
    # wait for start
    started_at = None
    poll_at = datetime.now()
    current_file = None
    current_file_writer = None
    is_recording = False
    while True:
        # read process data
        proc_resp = session.get(process_endpoint)
        if proc_resp.status_code != 200:
            raise Exception("Unexpected status code when polling process data", proc_resp.status_code)
        proc_msg = proc_resp.json()
        is_running =  proc_msg["globalStatus"]["running"]

        # check whether we need to start or stop the recording
        if is_running and not is_recording:
            # start a new file
            started_at = poll_at
            csvpath = build_filepath(args.folder, system_name, started_at)
            current_file = open(csvpath, 'w+', newline='')
            current_file_writer = csv.writer(current_file, dialect=csv_dialect)
            # write header
            current_file_writer.writerow(csv_mapping[:,0])
            if timestamp_after_csvheader is not None:
                current_file_writer.writerow([started_at.strftime(timestamp_after_csvheader)])
            is_recording = True
        if not is_running and is_recording:
            # close file
            current_file.close()
            current_file = None
            is_recording = False

        # add current data (if there is an open file)
        if current_file is not None:
            occured_at = poll_at - started_at
            current_file_writer.writerow([get_value(occured_at, proc_msg, m[1], m[2]) for m in csv_mapping])

        # delay execution so that we poll once every second
        poll_at = poll_at + timedelta(seconds=1)
        sleep_for = (poll_at - datetime.now()).total_seconds()
        if sleep_for > 0:
            time.sleep(sleep_for)