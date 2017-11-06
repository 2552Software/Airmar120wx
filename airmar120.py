#!/usr/bin/env python

from __future__ import with_statement
import serial
import syslog
import time

import weewx.drivers

DRIVER_NAME = 'Airmar 120wx'
DRIVER_VERSION = '0.1'

DEBUG_SERIAL = 1

def loader(config_dict, _):
    syslog.syslog(syslog.LOG_INFO, 'airmar: load %s' % DRIVER_NAME)
    return Airmar(**config_dict[DRIVER_NAME])

def confeditor_loader():
    return AirmarConfEditor()

class Airmar(weewx.drivers.AbstractDevice):
    """weewx driver that communicates with an Airmar Weather Station

    model: station model, e.g., 'Airmar 120WX'
    [Optional. Default is 'Airmar']

    port - serial port
    [Required. Default is /dev/ttyUSB0]

    max_tries - how often to retry serial communication before giving up
    [Optional. Default is 10]
    """
    def __init__(self, **stn_dict):
        self.model = stn_dict.get('model', 'Airmar')
        self.port = stn_dict.get('port', '/dev/ttyUSB0')
        self.max_tries = int(stn_dict.get('max_tries', 10))
        self.retry_wait = int(stn_dict.get('retry_wait', 10))
        self.last_rain = None

        global DEBUG_SERIAL
        DEBUG_SERIAL = int(stn_dict.get('debug_serial', 0))
        syslog.syslog(syslog.LOG_INFO,'airmar: driver version %s' % DRIVER_VERSION)
        syslog.syslog(syslog.LOG_INFO,'airmar: serial port %s' % self.port)
        self.station = Station(self.port)
        self.station.open()

    def closePort(self):
        if self.station is not None:
            self.station.close()
            self.station = None

    @property
    def hardware_name(self):
        return self.model

    def genLoopPackets(self):
        while True:
            syslog.syslog(syslog.LOG_DEBUG, 'airmar: genLoopPackets')
            packet = {'dateTime': int(time.time() + 0.5),
                      'usUnits': weewx.US}
            readings = self.station.get_readings_with_retry(self.max_tries,
                                                            self.retry_wait)
            #data = Station.parse_readings(readings)
            data = self.station.parse_readings(readings)
            packet.update(data)
            self._augment_packet(packet)
            yield packet

    def _augment_packet(self, packet):
        # no wind direction when wind speed is zero
        if 'windSpeed' in packet and not packet['windSpeed']:
            packet['windDir'] = None

class Station(object):
    def __init__(self, port):
        self.port = port
        self.baudrate = 4800
        self.timeout = 3 # seconds
        self.serial_port = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, _, value, traceback):
        self.close()

    def open(self):
        syslog.syslog(syslog.LOG_DEBUG, 'airmar: close serial port %s'  % self.port)
        if "://" in self.port:
           self.serial_port = serial.serial_for_url(self.port,
                                baudrate=self.baudrate,timeout=self.timeout)
        else:
          self.serial_port = serial.Serial(self.port, self.baudrate,
                                         timeout=self.timeout)

    def close(self):
        if self.serial_port is not None:
            syslog.syslog(syslog.LOG_DEBUG, 'airmar: open serial port %s'  % self.port)
            self.serial_port.close()
            self.serial_port = None

    def get_readings(self):
        syslog.syslog(syslog.LOG_DEBUG, 'airmar: get_readings')
        buf = self.serial_port.readline()
        buf = buf.strip() # FIXME: is this necessary?
        return buf

    #@staticmethod
    def parse_readings(self, raw):
        """Airmar.......
        """
        print raw
        data = dict()
        yx_data = dict()
        data['long_term_rain'] = None
        (interm, cs) = raw.split("*")
        buf = interm.split(",")
        if buf[0] == '$WIMDA': #  Meteorological Composite   Air Temp, Barometric Preasure
            try:
                data['altimeter'] = float(buf[1])
                data['outTemp'] = float(buf[5]) * 1.8 + 32
            except (ValueError):
                syslog.syslog(syslog.LOG_ERR, "airmar: Wrong data format for $WIMDA '%s, %s, %s, %s, %s, %s, %s'" % (buf[1], buf[5], buf[9], buf[11], buf[13], buf[15], buf[17]))
        elif buf[0] == '$WIMWV': # Wind Speed and Angle
            if buf[5] == 'A':
                if buf[2] == 'R':
                    try:
                        data['windAngle_rel_mwv'] = float(buf[1])
                        data['windSpeed_rel_mwv'] = float(buf[3]) / 1.15077945
                    except (ValueError):
                        syslog.syslog(syslog.LOG_ERR, "airmar: Wrong data format for $WIMWV A-R '%s, %s'" % (buf[1], buf[3]))
                elif buf[2] == 'T':
                    try:
                        data['windAngle_theor_mwv'] = float(buf[1])
                        data['windSpeed_theor_mwv'] = float(buf[3]) / 1.15077945
                    except (ValueError):
                        syslog.syslog(syslog.LOG_ERR, "airmar: Wrong data format for $WIMWV A-T '%s, %s'" % (buf[1], buf[3]))
                    
        #else: #Processing of other data sentences
        if 'windDir_true_mwd' in data and data['windDir_true_mwd'] is not None:
            data['windDir'] = data['windDir_true_mwd']
        elif 'windDir_true_mda' in data and data['windDir_true_mda'] is not None:
            data['windDir'] = data['windDir_true_mda']

        if 'windSpeed_mwd' in data and data['windSpeed_mwd'] is not None:
            data['windSpeed'] = data['windSpeed_mwd']
        elif 'windSpeed_mda' in data and data['windSpeed_mda'] is not None:
            data['windSpeed'] = data['windSpeed_mda']

        return data

class AirmarConfEditor(weewx.drivers.AbstractConfEditor):
    @property
    def default_stanza(self):
        return """
[Airmar]
    # This section is for the Airmar series of weather stations.

    # Serial port such as /dev/ttyS0, /dev/ttyUSB0, or /dev/cuaU0
    port = /dev/ttyUSB0

    # The station model, e.g., Airmar 120WX
    model = Airmar120WX

    # The driver to use:
    driver = weewx.drivers.airmar
"""

    def prompt_for_settings(self):
        print "Specify the serial port on which the station is connected, for"
        print "example /dev/ttyUSB0 or /dev/ttyS0."
        port = self._prompt('port', '/dev/ttyUSB0')
        return {'port': port}


# define a main entry point for basic testing of the station without weewx
# engine and service overhead.  invoke this as follows from the weewx root dir:
#
# PYTHONPATH=bin python bin/weewx/drivers/airmar.py

if __name__ == '__main__':
    import optparse

    usage = """%prog [options] [--help]"""

    syslog.openlog('airmar', syslog.LOG_PID | syslog.LOG_CONS)
    syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_DEBUG))
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('--version', dest='version', action='store_true',
                      help='display driver version')
    parser.add_option('--port', dest='port', metavar='PORT',
                      help='serial port to which the station is connected',
                      default=DEFAULT_PORT)
    (options, args) = parser.parse_args()

    if options.version:
        print "airmar driver version %s" % DRIVER_VERSION
        exit(0)

    with Station(options.port) as s:
        s.set_logger_mode()
        while True:
            print time.time(), s.get_readings()
