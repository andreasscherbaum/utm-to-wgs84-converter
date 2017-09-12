#!/usr/bin/env python3
#
# read file with UTM coordinates and transform them into lat/long
#
# written by Andreas 'ads' Scherbaum <andreas@scherbaum.la>



import re
import os
import sys
if sys.version_info[0] < 3:
    reload(sys)
    sys.setdefaultencoding('utf8')
import logging
import math
import stat
import argparse
import yaml
# this includes the functions which do the real coordinate transformation
from pyproj import Proj, transform, Geod
#import pyproj


# start with 'info', can be overriden by '-q' later on
logging.basicConfig(level = logging.INFO,
		    format = '%(levelname)s: %(message)s')






#######################################################################
# Config class

class Config:

    def __init__(self):
        self.__cmdline_read = 0
        self.__configfile_read = 0
        self.arguments = False
        self.argument_parser = False
        self.configfile = False
        self.config = False
        self.output_help = True

        if (os.environ.get('HOME') is None):
            logging.error("$HOME is not set!")
            sys.exit(1)
        if (os.path.isdir(os.environ.get('HOME')) is False):
            logging.error("$HOME does not point to a directory!")
            sys.exit(1)



    # config_help()
    #
    # flag if help shall be printed
    #
    # parameter:
    #  - self
    #  - True/False
    # return:
    #  none
    def config_help(self, config):
        if (config is False or config is True):
            self.output_help = config
        else:
            print("")
            print("invalid setting for config_help()")
            sys.exit(1)



    # print_help()
    #
    # print the help
    #
    # parameter:
    #  - self
    # return:
    #  none
    def print_help(self):
        if (self.output_help is True):
            self.argument_parser.print_help()



    # parse_parameters()
    #
    # parse commandline parameters, fill in array with arguments
    #
    # parameter:
    #  - self
    # return:
    #  none
    def parse_parameters(self):
        parser = argparse.ArgumentParser(description = 'Parse CSV file with data for OpenStreetMap',
                                         add_help = False)
        self.argument_parser = parser
        parser.add_argument('--help', default = False, dest = 'help', action = 'store_true', help = 'show this help')
        parser.add_argument('-c', '--config', default = '', dest = 'config', help = 'configuration file', required = True)
        parser.add_argument('-d', '--data', default = '', dest = 'data', help = 'data file', required = True)
        # store_true: store "True" if specified, otherwise store "False"
        # store_false: store "False" if specified, otherwise store "True"
        parser.add_argument('-v', '--verbose', default = False, dest = 'verbose', action = 'store_true', help = 'be more verbose')
        parser.add_argument('-q', '--quiet', default = False, dest = 'quiet', action = 'store_true', help = 'run quietly')


        # parse parameters
        args = parser.parse_args()

        if (args.help is True):
            self.print_help()
            sys.exit(0)

        if (args.verbose is True and args.quiet is True):
            self.print_help()
            print("")
            print("Error: --verbose and --quiet can't be set at the same time")
            sys.exit(1)

        if not (args.config):
            self.print_help()
            print("")
            print("Error: configfile is required")
            sys.exit(1)

        if not (args.data):
            self.print_help()
            print("")
            print("Error: data file is required")
            sys.exit(1)

        if (args.verbose is True):
            logging.getLogger().setLevel(logging.DEBUG)

        if (args.quiet is True):
            logging.getLogger().setLevel(logging.ERROR)

        self.__cmdline_read = 1
        self.arguments = args

        return



    # load_config()
    #
    # load configuration file (YAML)
    #
    # parameter:
    #  - self
    # return:
    #  none
    def load_config(self):
        if not (self.arguments.config):
            return

        logging.debug("config file: " + self.arguments.config)

        if (self.arguments.config and os.path.isfile(self.arguments.config) is False):
            self.print_help()
            print("")
            print("Error: --config is not a file")
            sys.exit(1)

        # the config file holds sensitive information, make sure it's not group/world readable
        st = os.stat(self.arguments.config)
        if (st.st_mode & stat.S_IRGRP or st.st_mode & stat.S_IROTH):
            self.print_help()
            print("")
            print("Error: --config must not be group or world readable")
            sys.exit(1)


        try:
            with open(self.arguments.config, 'r') as ymlcfg:
                config_file = yaml.safe_load(ymlcfg)
        except:
            print("")
            print("Error loading config file")
            sys.exit(1)


        self.configfile = config_file
        self.config = config_file
        self.__configfile_read = 1

        return



    # get1()
    #
    # get a specific 1st level config setting
    #
    # parameter:
    #  - self
    #  - config setting name
    # return:
    #  - config value
    # note:
    #  - will abort if the configuration is not yet initialized
    #  - will abort if the config setting is not initialized
    def get1(self, name1):
        if (self.__configfile_read != 1):
            print("")
            print("Error: config is not initialized!")
            sys.exit(1)
        if (name1 in self.config):
            return self.config[name1]
        else:
            print("")
            print("Error: requested config value does not exist!")
            print("Value: " + name1)
            sys.exit(1)



    # get2()
    #
    # get a specific 2nd level config setting
    #
    # parameter:
    #  - self
    #  - config setting name 1
    #  - config setting name 2
    # return:
    #  - config value
    # note:
    #  - will abort if the configuration is not yet initialized
    #  - will return None if the config setting is not set
    def get2(self, name1, name2):
        if (self.__configfile_read != 1):
            print("")
            print("Error: config is not initialized!")
            sys.exit(1)
        if (name1 in self.config):
            if (name2 in self.config[name1]):
                return self.config[name1][name2]
            else:
                return None
        else:
            return None


# end Config class
#######################################################################




def bye1(error1):
    print("")
    print(error1)
    print("")
    sys.exit(1)


def bye2(error1, error2):
    print("")
    print(error1)
    print("")
    print(error2)
    print("")
    sys.exit(1)



# transform_utm_into_lat_lon()
#
# do the coordinate transformation
#
# parameter:
#  - UTM x coordinate
#  - UTM y coordinate
#  - UTM zone
#  - UTM hemisphere (N/S)
# return:
#  - longitude, latitude
def transform_utm_into_lat_lon(x, y, zone, hemisphere):

    # verify the hemisphere
    h_north = False
    h_south = False
    if (hemisphere == 'N'):
        h_north = True
    elif (hemisphere == 'S'):
        h_south = True
    else:
        bye1("Unknown hemisphere: " + hemisphere)

    proj_in = Proj(proj = 'utm', zone = zone, ellps = 'WGS84', south = h_south, north = h_north, errcheck = True)

    lon, lat = proj_in(x, y, inverse = True)

    # just printing the floating point number with 6 decimal points will round it
    lon = math.floor(lon * 1000000) / 1000000
    lat = math.floor(lat * 1000000) / 1000000

    lon = "%.6f" % lon
    lat = "%.6f" % lat

    return lon, lat



# lat_lon_distance()
#
# calculates the distance (in meters) between two lat/lon coordinates
#
# parameter:
#  - latitude of coordinate 1
#  - longitude of coordinate 1
#  - latitude of coordinate 2
#  - longitude of coordinate 2
# return:
#  distance in meters
def lat_lon_distance(lat1, lon1, lat2, lon2):
    geo = Geod(ellps = 'WGS84')
    # azimuth, back azimuth, distance
    azimuth, back_azimuth, distance = geo.inv(lon1, lat1, lon2, lat2)

    return distance



# upload_data()
#
# handles one set of input data
#
# parameter:
#  - text field from input data
#  - x coordinate (either UTM or WGS84)
#  - y coordinate (either UTM or WGS84)
# return:
#  - false (no error) / true (error)
def upload_data(name, x, y):
    is_error = False
    logging.info(name)
    if (coordinates_format == 'utm'):
        # coordinates must be transformed first
        logging.debug("  UTM: " + str(x) + " / " + str(y))
        lon, lat = transform_utm_into_lat_lon(x, y, coordinates_zone, coordinates_hemisphere)
        logging.debug("  WGS84: " + str(lat) + " / " + str(lon))
    else:
        lon = x
        lat = y
        logging.debug("  WGS84: " + str(lat) + " / " + str(lon))
    distance = lat_lon_distance(lat, lon, center_lat, center_lon)
    logging.debug("  " + str("%.2f" % distance) + " meters from '" + str(center_name) + "'")
    #print("Point: " + str(lat) + "," + str(lon) + "," + str(name) + "," + str(str(lat) + " " + str(lon)) + "," + str("%.2fm" % distance))
    if (distance > center_max_distance):
        logging.error("  Exceeds maximum allowed distance by " + str(int(distance - center_max_distance)) + " meters")
        is_error = True
    print("")
    sys.stdout.flush()
    sys.stderr.flush()

    return is_error




config = Config()
config.parse_parameters()
config.load_config()


# read coordinate format from config file
coordinates_format = config.get2('coordinates', 'format')
if (coordinates_format is None):
    bye2("Please set the coordinate system format in the config file", "Must be one of 'utm' or 'wgs84")

# UTM coordinated require an additional zone name and hemisphere
if (coordinates_format == 'utm'):
    coordinates_zone = config.get2('coordinates', 'zone')
    if (coordinates_zone is None):
        bye1("UTM coordinate system requires a 'zone' specification")
    try:
        if (coordinates_zone != int(coordinates_zone)):
            bye1("'zone' specification must be an integer")
    except ValueError:
        bye1("'zone' specification must be an integer")

    coordinates_hemisphere = config.get2('coordinates', 'hemisphere')
    if (coordinates_hemisphere is None):
        bye1("UTM coordinate system requires a 'hemisphere' specification")
    if (coordinates_hemisphere != 'N' and coordinates_hemisphere != 'S'):
        bye1("UTM coordinate system requires a 'hemisphere' specification")



# data is verified by calculating distance to a given set of coordinates
center_name = config.get2('center location', 'name')
if (center_name is None):
    bye1("Specify a name for the coordinates center")

center_lat = config.get2('center location', 'lat')
if (center_lat is None):
    bye1("Specify a latitude for the coordinates center")
center_lon = config.get2('center location', 'lon')
if (center_lon is None):
    bye1("Specify a longitude for the coordinates center")

center_max_distance = config.get2('center location', 'max distance')
if (center_max_distance is None):
    bye1("Specify a maximum distance for the coordinates center")


# this allows specifying the column positions in the input file
input_name = config.get2('input', 'name')
if (input_name is None):
    bye1("Specify a column for the name in the input file")
try:
    if (input_name != int(input_name)):
        bye1("input name column must be an integer")
except ValueError:
    bye1("input name column must be an integer")

input_x = config.get2('input', 'x')
if (input_x is None):
    bye1("Specify a column for the x coordinates in the input file")
try:
    if (input_x != int(input_x)):
        bye1("input x column must be an integer")
except ValueError:
    bye1("input x column must be an integer")

input_y = config.get2('input', 'y')
if (input_y is None):
    bye1("Specify a column for the y coordinates in the input file")
try:
    if (input_y != int(input_y)):
        bye1("input y column must be an integer")
except ValueError:
    bye1("input y column must be an integer")

# data file might have a header
input_header = config.get2('input', 'header')
if (input_header is None):
    bye1("Specify if the input file has a header")
try:
    if (input_header is not True and input_header is not False):
        bye1("input header column must be a flag")
except ValueError:
    bye1("input header column must be a flag")


if (input_name == input_x or input_name == input_y or input_x == input_y):
    bye1("Overlapping column numbers")



# finally read the input file
with open(config.arguments.data) as f:
    logging.debug("data file: " + str(config.arguments.data))
    line_number = 0
    lines_parsed = 0
    lines_ok = 0
    lines_error = 0
    for line in f:
        line_number += 1
        # only if a header line is specified: skip the first line
        if (input_header is True and line_number == 1):
            continue
        lines_parsed += 1
        #print(line.rstrip('\n'))
        line = line.rstrip("\n")
        line_data = line.split("\t")
        ret = upload_data(line_data[input_name - 1], line_data[input_x - 1], line_data[input_y - 1])
        if (ret is False):
            lines_ok += 1
        else:
            lines_error += 1
        #sys.exit(0)
    print("")
    logging.info("   Lines read: " + str(line_number))
    logging.info(" Lines parsed: " + str(lines_parsed))
    logging.info("Without error: " + str(lines_ok))
    logging.info("   With error: " + str(lines_error))






# http://www.rcn.montana.edu/resources/converter.aspx

# Latitude: north–south position of a point on Earth
# Longitude: east-west position of a point on Earth
# Easting: eastward-measured distance (or the x-coordinate)
# Northing: northward-measured distance (or the y-coordinate)
