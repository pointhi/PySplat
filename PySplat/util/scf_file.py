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

import re


_scf_entry_match = re.compile("^\s*([0-9]+):\s*([0-9]+),\s*([0-9]+),\s*([0-9]+)\s*$")


default_scf_file = {
    128: (255, 0, 0),
    118: (255, 165, 0),
    108: (255, 206, 0),
    98: (255, 255, 0),
    88: (184, 255, 0),
    78: (0, 255, 0),
    68: (0, 208, 0),
    58: (0, 196, 196),
    48: (0, 148, 255),
    38: (80, 80, 255),
    28: (0, 38, 255),
    18: (142, 63, 255),
    8: (140, 0, 128)
}


def parse_scf_file(scf_file):
    signal_colors = {}

    with open(scf_file, "r") as file:
        for line in file.readlines():
            line = line.rstrip('\n')

            if line.startswith(';'):
                continue  # comment

            match = _scf_entry_match.match(line)

            if not match:
                print("unexpeced line: \"{0}\"".format(line))
                continue

            signal_colors[match.group(1)] = (match.group(2), match.group(3), match.group(4))

    return signal_colors