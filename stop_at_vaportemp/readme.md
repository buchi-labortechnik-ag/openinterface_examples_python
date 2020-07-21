# Stop at Vapor Temperature
stop_at_vaportemp.py is an example script that stops a rotavapor once a specified vapor temperature us reached.

## Usage
Run the python script from the console and pass in relevant arguments

```
usage: stop_at_vaportemp.py [-h] [-u USER] [-p PASSWORD] temp host

Stops rotavapor once specified vapor temp is reached.

positional arguments:
  temp                  vapor temp threshold in °C
  host                  host or IP of rotavapor

optional arguments:
  -h, --help            show this help message and exit
  -u USER, --user USER  device user (rw or ro)
  -p PASSWORD, --password PASSWORD
                        device password
```

## Customization
At the beginning of the script there are a few variables that can be changed in case something else than vacuum temp should serve as stop criterion.
```Python
# path to the relevant parameter in the process json
path_to_param = '$.vacuum.vaporTemp'
# pretty print name of parameter for help / console
param_name = 'vapor temp'
# pretty print unit of parameter for help / console
unit = '°C'
path_to_param_expr = parse(path_to_param)
# stop condition as lambda. first argument is the process json as dict, second the target value
condition = lambda proc_msg, target: jsonpath_expression.find(proc_msg)[0].value > target
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](../LICENSE)