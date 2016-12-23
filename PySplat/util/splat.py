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

import os
import subprocess
import tempfile


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


def run_splat(qth_obj, srtm_dir, output_file):
    #print("render splat map: {0} to {1}".format(qth_obj, output_file))

    # output path has to exist (otherwise SEGFAULT!)
    output_path = os.path.dirname(output_file)
    if not os.path.exists(output_path):
        print("create directory: {0}".format(output_path))
        os.makedirs(output_path)

    splat_call = ["splat"]
    splat_call += ["-t", os.path.abspath(qth_obj.qth_file)] # our qth file
    splat_call += ["-L",  "10.0"]  # we calculate path LOS for 10m above ground (TODO)
    splat_call += ["-d", os.path.abspath(srtm_dir)]  # path to topographic data
    splat_call += ["-R", "100"]  # limit range of calculation (TODO)
    splat_call += ["-ngs"]  # the heightmap only intereference with tile generation
    splat_call += ["-geo"]  # we need a .geo reference file, to create tiles later
    splat_call += ["-metric"]  # we want to use metric everywhere
    splat_call += ["-o", os.path.abspath(output_file)] # filename of topographic map to generate (.ppm)

    #print("run command: \"{0}\"".format(" ".join(splat_call)))

    tmp_dir = tempfile.mkdtemp("_pysplat")
    print("use tmp dir: {0}".format(tmp_dir))

    try:
        with subprocess.Popen(splat_call, cwd=tmp_dir, shell=False) as splat_sp:
            # TODO: , stdout=subprocess.PIPE
            splat_sp.wait()
            # TODO: get data and parse output

            print("return code: {0}".format(splat_sp.returncode))
            if splat_sp.returncode != 0:
                return

            site_reporter_file = os.path.join(tmp_dir, "{qth_filename}-site_report.txt".format(qth_filename=qth_obj.name))
            # print("remove file: {0}".format(site_reporter_file))
            os.remove(site_reporter_file)

    finally:
        # we want to delete the tmp folder in all cases
        os.rmdir(tmp_dir)