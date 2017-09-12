# utm-to-wgs84-converter

The _convert.py_ script reads lines with coordinates (and additional text field) from a file, and converts the coordinates into WGS84, if specified in UTM format.

## Usage

```
./convert.py -v -c config.yaml -d input.csv
```

The configuration is specified in _config.yaml_, and requires a "center coordinate" plus a maximum distance (in meters). Every input coordinate is verified against this coordinate, and if it exceeds the maximum distance, an error is raised. If you do not want any error checking, just raise the maximum distance to a very high value.

## Format of example input file:

```
	X	Y
Waste basket	367815.774857	5932106.01162
Waste basket	367723.190517	5932136.70537
```
