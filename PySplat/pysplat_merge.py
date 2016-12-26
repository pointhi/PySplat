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
import logging
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import time

sys.path.append(os.path.join(sys.path[0], "../")) # enable package import from parent directory

from PySplat.util.argparse_helper import check_thread_count
from PySplat.util.scf_file import parse_scf_file, default_scf_data, get_sorted_pixel_order


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class TileMerger(object):
    def __init__(self, image_order, threads):
        self._image_order = image_order
        self._max_queue_size = threads * 4
        self._executor = ThreadPoolExecutor(max_workers=threads)

    def submit_merge_images(self, sources, destination):
        while self._executor._work_queue.qsize() > self._max_queue_size:
            time.sleep(.01) # TODO: better apporach

        print("submit calculate tile: \"{0}\" using {1} source tiles".format(destination, len(sources)))
        self._executor.submit(self.merge_images, sources, destination)

    def wait_until_empty(self):
        while not self._executor._work_queue.empty():
            time.sleep(.01)

    def merge_images(self, sources, destination):
        print("calculate tile: \"{0}\" using {1}".format(destination, sources))
        time.sleep(1)
        source_images = []

        for single_source in sources:
            new_image = Image.open(single_source)
            source_images += [new_image]

        if len(source_images) > 1:
            destination_image = self.merge_loaded_images(source_images)
        else:
            destination_image = source_images[0].copy()

        destination_image.save(destination, "PNG")

    def merge_loaded_images(self, source_images):
        source_image_pixdata = []
        for single_source in source_images:
            source_image_pixdata += [single_source.load()]

        destination_image = source_images[0].copy()
        dest_pixdata = destination_image.load()

        for y in range(destination_image.size[1]):
            for x in range(destination_image.size[0]):
                for source_pixdata in source_image_pixdata[1:]:
                    if dest_pixdata[x, y] == (255, 255, 255, 0):
                        dest_pixdata[x, y] = source_pixdata[x, y]
                        continue

                    if source_pixdata[x, y] not in self._image_order:
                        continue

                    if dest_pixdata[x, y] not in self._image_order:
                        continue

                    # TODO: better merging
                    if self._image_order.index(source_pixdata[x, y]) < self._image_order.index(dest_pixdata[x, y]):
                        dest_pixdata[x, y] = source_pixdata[x, y]


'''
class OpenCLTileMerger(TileMerger):
    def __init__(self, image_order, threads):
        super.__init__(image_order, threads)

    def merge_loaded_images(self, source_images):
        # TODO: implement
        return super.merge_loaded_images(source_images)
'''


def merge_maps(src_dir, dest_dir, tile_merger, **kwargs):
    # get a list of files to merge
    files = {}
    for single_source in src_dir:
        new_files = filter(lambda x: os.path.isfile(os.path.join(single_source, x)) and x.endswith('.png'), os.listdir(single_source))
        for file in new_files:
            file_path = os.path.join(single_source, file)
            if file in files:
                files[file] = files[file] + [file_path]
            else:
                files[file] = [file_path]

    # merge files
    for key, src_files in files.items():
        dest_file = os.path.join(dest_dir, key)
        tile_merger.submit_merge_images(src_files, dest_file)

    # get all subfolders
    sub_level = set()
    for single_source in src_dir:
        new_level = filter(lambda x: os.path.isdir(os.path.join(single_source, x)), os.listdir(single_source))
        sub_level = sub_level.union(new_level)

    # enter all working subfolders
    for level in sorted(sub_level, key=int):
        new_dest_dir = os.path.join(dest_dir, str(level))

        print("enter dir: {0}".format(new_dest_dir))
        if not os.path.isdir(new_dest_dir):
            print("create dir: {0}".format(new_dest_dir))
            os.mkdir(new_dest_dir)

        new_src_dir = set()
        for single_src in src_dir:
            single_src_child = os.path.join(single_src, str(level))
            if os.path.exists(single_src_child):
                new_src_dir.add(single_src_child)

        merge_maps(new_src_dir, new_dest_dir, tile_merger)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('inputdirs', nargs="+", help='image file which should be converted', action='store')
    parser.add_argument('outputdir', help='output directory where we store the calculated tiles')
    parser.add_argument('--scf', dest='scffile', help='scf file required used for merging')
    parser.add_argument('-y', dest='threads', type=check_thread_count, default=1, help='number of threads')
    parser.add_argument('-v', '--verbose', help='show extra information', action='store_true')
    parser.add_argument('-d', '--debug', help='show debug informations', action='store_true')
    parser.add_argument('--gpu', help='run merge algorihm using gpu', action='store_true')

    args = parser.parse_args()

    for input_dir in args.inputdirs:
        if not os.path.exists(input_dir):
            print("{0} is not a existing directory".format(input_dir))
            sys.exit(1)

    output_dir = args.outputdir
    if not os.path.exists(output_dir):
        print("create directory: {0}".format(output_dir))
        os.makedirs(output_dir)

    scf_data = default_scf_data
    if args.scffile:
        if os.path.isfile(args.scffile):
            print("parse .scf file: {0}".format(args.scffile))
            scf_data = parse_scf_file(args.scffile)
        else:
            print("not a existing file: {0}".format(args.scffile))
            sys.exit(1)

    image_order = get_sorted_pixel_order(scf_data)

    tile_merger = TileMerger(image_order, args.threads)

    print("input dirs: {0}".format(args.inputdirs))
    print("output dir: {0}".format(output_dir))
    print("scf data: {0}".format(scf_data))

    merge_maps(args.inputdirs, output_dir, tile_merger)

    tile_merger.wait_until_empty()