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

class SplatQTH(object):
    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.qth_file = kwargs.get('qth_file') # qth definition
        self.lrp_file = kwargs.get('lrp_file') # location definition
        self.az_file = kwargs.get('az_file') # antenna azimut pattern
        self.el_file = kwargs.get('el_file') # antenna elevation pattern

    def __str__(self):
        files = []

        if self.qth_file:
            files.append('qth="{0}"'.format(self.qth_file))

        if self.lrp_file:
            files.append('lrp="{0}"'.format(self.lrp_file))

        if self.az_file:
            files.append('az="{0}"'.format(self.az_file))

        if self.el_file:
            files.append('el="{0}"'.format(self.el_file))

        return '{name}[{files}]'.format(name=self.name, files=', '.join(files) )