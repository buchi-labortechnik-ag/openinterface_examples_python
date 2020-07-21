# BUCHI OpenInterface and Python

## Introduction
BUCHI’s OpenInterface provides full and well documented access to all data an instrument produces and consumes. It provides approximately the same amount of functionality as can be accessed via the device’s on-screen menu. 

The OpenInterface is a RESTful HTTP API. The documentation of this API can be found [here](https://developer.buchi.com/rotavapor/openinterface/doc/).

This repository contains instructions and examples that show how to interact with your BUCHI Rotavapor using Python.

### Lab Device Requiements

#### Rotavapor R-300
BUCHI's Rotavapor R-300 line is a modular system. Any valid configuration will do as long it contains a [Interface I-300pro](https://www.buchi.com/en/products/laboratory-evaporation/interface-i-300-pro) with VacuBox.

Certain examples might have more specific requirements.

### Preparations
For running the examples you will need the following information:
* Valid Username/PW
* Device IP Address

Usernames and passwords are only shown at the time the OpenInterface is enabled. The IP address can be found via on-screen menus.

Please consult the [API Documentation](https://developer.buchi.com/rotavapor/openinterface/doc/) for more detailled instructions.

## Examples
* [CSV Recorder](./csv_recorder/)
* [Stop at a certain vapor temperature](./stop_at_vaportemp/)



## Basic usage
Easiest way to interact with a Rotavapor from Python is by using the requests package.

1. Create a requests session

    ```python
    import requests
    session = requests.Session()
    ```
2. Specify username and password

    ```python
    session.auth = ('user', 'password')
    ```
3. Provide the OpenInterface root cert or disable cert checks

    ```python
    rootcert = 'path/to/root.crt'
    if path.isfile(rootcert):
        session.verify = rootcert
    else:
        session.verify = False
    ```
4. Either read some data
    ```python
    rotavapor_ip = '192.168.1.234'
    base_url = f"https://{rotavapor_ip}/api/v1"
    info_endpoint = base_url + "/info"
    get_info_resp = session.get(info_endpoint)
    info_msg = info_endpoint.json()
    system_name = info_msg["systemName"]
    print(f"The name of the device is {system_name}")
    ```
5. Or write some data
    ```python
    rotavapor_ip = '192.168.1.234'
    base_url = f"https://{rotavapor_ip}/api/v1"
    process_endpoint = base_url + "/process"
    set_vacuum_msg = { 'vacuum' : { 'set' : 100 } }
    set_vacuum_resp = session.put(process_endpoint, json=set_vacuum_msg)
    ```

Details about the schema of requests / replies can be found in the  [API Documentation](https://developer.buchi.com/rotavapor/openinterface/doc/)

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
All examples are licensed under the MIT License - see the [LICENSE](LICENSE) file for details.