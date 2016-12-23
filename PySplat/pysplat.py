#!/usr/bin/env python
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

import argparse, sys, os
import ntpath
import logging
import concurrent

from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.join(sys.path[0], "../")) # enable package import from parent directory

from PySplat.util.splat import SplatQTH, run_splat


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def create_qth_file_obj(file):
    qth_name = ntpath.basename(file)[:-4]

    lrp_file = file[:-4] + ".lrp"  # location definition
    if not os.path.isfile(lrp_file):
        lrp_file = None

    az_file = file[:-4] + ".az"  # antenna azimut pattern
    if not os.path.isfile(az_file):
        az_file = None

    el_file = file[:-4] + ".el"  # antenna elevation pattern
    if not os.path.isfile(el_file):
        el_file = None

    scf_file = file[:-4] + ".scf"  # Signal Color Definition
    if not os.path.isfile(scf_file):
        scf_file = None

    return SplatQTH(name=qth_name, qth_file=file, lrp_file=lrp_file, az_file=az_file, el_file=el_file)


def get_qth_files(qht_file):
    if not qht_file:
        return {}

    qth_obj = []

    for single_qth_file in qht_file:
        logger.debug('evaluate file: {0}'.format(single_qth_file))

        if not single_qth_file.endswith('.qth'):
            logger.warning('txsite file doesn\'t end with *.qth: "{single_qth_file}"'.format(single_qth_file=single_qth_file))
            continue

        if not os.path.isfile(single_qth_file):
            logger.error('invalid txsite file: "{single_qth_file}"'.format(single_qth_file=single_qth_file))
            continue;

        new_splat_obj = create_qth_file_obj(single_qth_file)

        logger.info('Add TX-Site: {0}'.format(new_splat_obj))

        qth_obj.append(new_splat_obj)

    return qth_obj


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser()

        parser.add_argument('qth', nargs='+', help='txsite(s).qth', action='store')
        parser.add_argument('--out', dest='outputdir', default='./', help='output directory where we store the calculated data')
        parser.add_argument('--srtm', dest='srtmdir', default='./srtm', help='directory where srtm data is stored')
        parser.add_argument('-y', type=int, default=1, choices=range(1,256), help='number of threads')
        parser.add_argument('-v', '--verbose', help='show extra information', action='store_true')
        parser.add_argument('-d', '--debug', help='show debug informations', action='store_true')

        args = parser.parse_args()

        if args.verbose:
            logger.setLevel(logging.INFO)

        if args.debug:
            logger.setLevel(logging.DEBUG)

        qth_files = get_qth_files(args.qth)

        with ThreadPoolExecutor(max_workers=args.y) as executor:
            futures = []
            try:
                # create threads
                for qth in qth_files:
                    futures += [executor.submit(run_splat, qth, args.srtmdir, os.path.join(args.outputdir, '{name}.ppm'.format(name=qth.name)))]

                # wait until finished
                # TODO: http://stackoverflow.com/questions/29177490/how-do-you-kill-futures-once-they-have-started
                concurrent.futures.wait(futures)

            except Exception as e:
                print("except: {0}".format(e))

    except KeyboardInterrupt:
        pass