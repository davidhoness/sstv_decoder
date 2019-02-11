#!/usr/bin/python3
import urllib.request
import math
import socket
import ephem
import time
import sys
import ssl


C = 300000000.0
F0 = 145800000.0

LATITUDE = "52.219308"
LONGITUDE = "4.419926"
ALTITUDE = 20


class tle_reader(object):
    """
    For keeping ephem two line element sets up to date
    """
    def __init__(self,
                 tle_name="ISS (ZARYA)",
                 tle_file="https://celestrak.com/NORAD/elements/stations.txt",
                 tle_max_age=3600):
        self._tle_name = tle_name
        self._tle_file = tle_file
        self._tle_max_age = tle_max_age
        self._tle = None
        self.reload()

    def build_index(self, tle_lines):
        index = {}
        for i in range(0, len(tle_lines), 3):
            index[tle_lines[i].strip()] = (tle_lines[i + 1], tle_lines[i + 2])
        return index

    def reload(self):
        print("Loading: %s" % self._tle_file)

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(self._tle_file, context=ctx) as response:
                tle_lines = response.read().decode("utf-8").splitlines()
            index = self.build_index(tle_lines)
            tle_data = index[self._tle_name]
            self._tle = ephem.readtle(self._tle_name, tle_data[0], tle_data[1])
        except Exception as e:
            print(e)

        self._tle_age = time.time()

    @property
    def tle(self):
        return self._tle

    @property
    def tle_expired(self):
        return time.time() - self._tle_age > self._tle_max_age


class rtl_fm_remote(object):
    """
    For remote control of rtl_fm command line program
    """
    def __init__(self,
                 host="localhost",
                 port=6020):
        self._host = host
        self._port = port
        self._s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._s.connect((self._host, self._port))

    def set_freq(self, freq):
        self.send_cmd(0, freq)

    def set_mode(self, mode):
        self.send_cmd(1, mode)

    def set_squelch(self, squelch):
        self.send_cmd(2, squelch)

    def set_gain(self, gain):
        self.send_cmd(3, gain)

    def send_cmd(self, cmd, param):
        cmd_bytes = (cmd).to_bytes(1, "little")
        param_bytes = (param).to_bytes(32, "little")
        self._s.send(cmd_bytes + param_bytes)

    def __del__(self):
        self._s.close()


rtl = rtl_fm_remote()
iss = tle_reader(tle_name="ISS (ZARYA)", tle_max_age=5520)  # 92 minutes

if iss.tle is None:
    sys.exit(0)

myloc = ephem.Observer()
myloc.lon = LONGITUDE
myloc.lat = LATITUDE
myloc.elevation = ALTITUDE

freq = F0
running = True

try:
    while running:
        myloc.date = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime())
        iss.tle.compute(myloc)
        alt = math.degrees(iss.tle.alt)

        if alt > 0:  # iss is flying over our location
            new_freq = int(F0 - iss.tle.range_velocity * F0 / C)  # doppler
            if new_freq != freq:
                print(new_freq, round(alt, 2), myloc.date)
                rtl.set_freq(new_freq)  # set new frequency in rtl_fm
            freq = new_freq
        elif iss.tle_expired:
            iss.reload()  # we could be running for days / weeks
        else:
            time.sleep(10)  # do nothing, wait for iss to arrive
            freq = F0
except KeyboardInterrupt:
    running = False

print("Bye")
