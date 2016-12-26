'''
pysplat is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pysplat is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with kicad-footprint-generator. If not, see < http://www.gnu.org/licenses/ >.

(C) 2016 by Thomas Pointhuber, <thomas.pointhuber@gmx.at>
'''

import argparse
import re


_zoom_level_regex = re.compile("^([0-9]+)-([0-9]+)$")


def check_thread_count(value):
    ivalue = int(value)
    if ivalue < 1:
         raise argparse.ArgumentTypeError("thread count has to be >= 1")
    return ivalue


def check_zoom_level(value):
    levels = []
    if value.isdigit():
        levels += [int(value)]
    elif _zoom_level_regex.match(value):
        match = _zoom_level_regex.match(value)
        print('matches: {0}-{1}'.format(match.groups(0)[0], match.groups(0)[1]))
        levels += range(int(match.groups(0)[0]), int(match.groups(0)[1]) + 1)
    else:
        raise argparse.ArgumentTypeError("zoom level has to be written in single levels, or as interval 1-12")
    return levels