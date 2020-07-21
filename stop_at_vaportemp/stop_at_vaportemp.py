import requests
import argparse
import getpass
from datetime import datetime, timedelta
import time
import urllib3
from os import path
from jsonpath_ng import jsonpath, parse

# path to the relevant parameter in the process json
path_to_param = '$.vacuum.vaporTemp'
# name of parameter for help / console
param_name = 'vapor temp'
# unit of parameter for help / console
unit = '°C'
path_to_param_expr = parse(path_to_param)
# stop condition as lambda. first argument is the process json as dict, second the target value
condition = lambda proc_msg, target: path_to_param_expr.find(proc_msg)[0].value > target

if __name__ == "__main__":
    # parse command line arguments
    parser = argparse.ArgumentParser(description=f'Stops rotavapor once specified {param_name} is reached.')
    parser.add_argument('temp', type=float, help=f'{param_name} threshold in {unit}')
    parser.add_argument('host', type=str, help='host or IP of rotavapor')
    parser.add_argument('-u', '--user', type=str, help='device user (rw or ro)', default='rw')
    parser.add_argument('-p', '--password', type=str, help='device password', required=False)
    args = parser.parse_args()

    # ask for password if it wasn't passed in as command line argument
    if args.password is None:
        args.password = getpass.getpass()

    auth = (args.user, args.password)
    base_url = f"https://{args.host}/api/v1"
    info_endpoint = base_url + "/info"
    process_endpoint = base_url + "/process"
    target_value = args.temp
    rootcert = "root_cert.crt"

    # configure http client session
    session = requests.Session()
    session.auth = auth
    if path.isfile(rootcert):
        # if there is a root certificate file we'll use that one
        session.verify = rootcert
    else:
        # ... if not, we'll ignore certificate errors
        print("Root certificate missing. Disabling certificate checks...")
        session.verify = False
        # this would cause warnings on the console which we disable here
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

        
    # wait for condition and stop
    poll_at = datetime.now()
    while True:
        # read temperature
        proc_resp = session.get(process_endpoint)
        if proc_resp.status_code != 200:
            raise Exception("Unexpected status code when polling process data", proc_resp.status_code)
        proc_msg = proc_resp.json()

        # check of we reached target temperature
        if condition(proc_msg, target_value):
            print(f"{param_name} of {target_value} {unit} has been reached.")
            # send stop message
            stop_msg = { 'globalStatus' : { 'running' : False } }
            proc_put_resp = session.put(process_endpoint, json=stop_msg)
            if proc_put_resp.status_code != 200:
                raise Exception("Unexpected status code when trying to stop rotavapor", proc_put_resp.status_code)
            break

        # delay execution so that we poll once every second
        poll_at = poll_at + timedelta(seconds=1)
        sleep_for = (poll_at - datetime.now()).total_seconds()
        if sleep_for > 0:
            time.sleep(sleep_for)


