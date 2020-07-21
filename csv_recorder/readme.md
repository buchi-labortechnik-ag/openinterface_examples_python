# CSV Recorder
csv_recorder.py is an example script that logs your rotavapor's data into CSV files.

## Usage
Run the python script from the console and pass in relevant arguments

```
usage: csv_recorder.py [-h] [-u USER] [-p PASSWORD] [-f FOLDER] [-c CERT] host
```

### Command Aruments
`csv_recorder.py -h` provides a list of arguments:
```
Remotely logs rotavapor process data into a CSV file. The format is the same
as the I-300pro writes to its SD card.

positional arguments:
  host                  host or IP of rotavapor

optional arguments:
  -h, --help            show this help message and exit
  -u USER, --user USER  device password
  -p PASSWORD, --password PASSWORD
                        device password
  -f FOLDER, --folder FOLDER
                        destination folder for the csv files
  -c CERT, --cert CERT  root cert file
```

## Customization
There is a mapping table that defines what is written into the CSV file:
```python
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
```

There are also some further options about CSV format:
```python
csv_dialect = csv.excel # see https://docs.python.org/3/library/csv.html#dialects-and-formatting-parameters
timestamp_after_csvheader = "%d.%m.%Y %H:%M" # set this to None if you don't wan't this second header line
missing_value_char = '*' #set this to None for an empty cell
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](../LICENSE)