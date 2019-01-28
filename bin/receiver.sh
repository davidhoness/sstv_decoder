#!/bin/bash
rtl_fm -f 145.8M -M fm -s 170k -A fast -l 0 | play -r 170k -t raw -e s -b 16 -c 1 -V1 -
