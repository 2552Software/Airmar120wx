!/usr/bin/env python


from __future__ import with_statement
import serial
import syslog
import time

import weewx.drivers

DRIVER_NAME = 'Airmar 120wx'
DRIVER_VERSION = '0.27'

INHG_PER_BAR = 29.5333727
METER_PER_FOOT = 0.3048
MILE_PER_KM = 0.621371

DEBUG_SERIAL = 0

def loader(config_dict, _):
    return Airmar(**config_dict[DRIVER_NAME])

def confeditor_loader():
    return AirmarConfEditor()

def logmsg(level, msg):
    syslog.syslog(level, 'airmar: %s' % msg)

def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)

def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)

def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)

class Airmar(weewx.drivers.AbstractDevice):
    """weewx driver that communicates with an Airmar Weather Station

    model: station model, e.g., 'Airmar 120WX'
    [Optional. Default is 'Airmar 120WX']

    port - serial port
    [Required. Default is /dev/ttyUSB0]

    max_tries - how often to retry serial communication before giving up
    [Optional. Default is 10]
    """
