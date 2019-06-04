#!/usr/bin/python3
import urllib.request
import subprocess
import math
import socket
import ephem
import time
import sys
import ssl
import os
import signal
import datetime

LATITUDE = "52.219308"
LONGITUDE = "4.419926"
ALTITUDE = 20

MODE = "fm"
FREQ = "145.8M"
RATE = "48k"

FILE_FMT = "%Y_%m_%d-%H-%M-%S.raw"

rtl_cmd = ["rtl_fm", "-M", MODE, "-f", FREQ, "-s", RATE]

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


iss = tle_reader(tle_name="ISS (ZARYA)", tle_max_age=5520)  # 92 minutes

if iss.tle is None:
    sys.exit(0)

myloc = ephem.Observer()
myloc.lon = LONGITUDE
myloc.lat = LATITUDE
myloc.elevation = ALTITUDE

running = True

while running:
    myloc.date = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime())
    iss.tle.compute(myloc)
    alt = math.degrees(iss.tle.alt)
    
    if alt > 0:  # iss is flying over our location
        fn = datetime.datetime.utcnow().strftime(FILE_FMT)
        f = open(fn, "wb")
        proc = subprocess.Popen(rtl_cmd, stdout=f)
        while alt > 0:
            myloc.date = time.strftime('%Y/%m/%d %H:%M:%S', time.gmtime())
            iss.tle.compute(myloc)
            alt = math.degrees(iss.tle.alt)
            time.sleep(10)
        f.flush()
        os.kill(proc.pid, signal.SIGTERM)
        proc.wait()
        f.close()
    elif iss.tle_expired:
        iss.reload()  # we could be running for days / weeks
    else:
        time.sleep(10)  # do nothing, wait for iss to arrive
