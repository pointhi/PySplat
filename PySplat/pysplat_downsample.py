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

sys.path.append(os.path.join(sys.path[0], "../")) # enable package import from parent directory

from PySplat.util.argparse_helper import check_thread_count, check_zoom_level
from PySplat.util.slippy_map_math import deg2num, num2deg

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


_blank_image = Image.new('RGBA', (256, 256), color=(255, 255, 255, 0))


def merge(image_tl, image_tr, image_bl, image_br):
    result_image = Image.new('RGBA', (256*2, 256*2))

    result_image.paste(image_tl, (0, 0))
    result_image.paste(image_tr, (256, 0))
    result_image.paste(image_bl, (0, 256))
    result_image.paste(image_br, (256, 256))

    return result_image.resize((256, 256))


def downsample(base_dir, tile, zoom, base_zoom, zoom_levels):
    '''
    TODO: the algorithm is based on the idea of deep search, but we are currently searching way to much dead ends.

    The Basic idea about deep merge is that we have to load tiles only once, and then we can calculate tiles
    of a lower zoom range based on images which are already loaded into RAM, and we have them loaded inside RAM
    for a minimum amount of time (fast as well as memory-saving methode for subsampling big amounts of tiles)

    Our problem is that at the moment, the algorithm checks for existance of all base_tiles
    (which are 2 ** (2*base_zoom) ) tiles. We should build some sort of boundingboxes, which marks where we could
    probably find tiles, and abort the deep search algorithm as soon as possible for us.
    '''
    result_dir = os.path.join(base_dir, str(zoom), str(tile[0]))
    result_filename = os.path.join(result_dir, "{0}.png".format(tile[1]))

    if zoom == base_zoom:
        if not os.path.isfile(result_filename):
            #print("return empty: {0}".format(result_filename))
            return _blank_image
        print("open: {0}".format(result_filename))
        return Image.open(result_filename)

    image_tl = downsample(base_dir, (tile[0] * 2, tile[1] * 2), zoom + 1, base_zoom, zoom_levels)
    image_tr = downsample(base_dir, (tile[0] * 2 + 1, tile[1] * 2), zoom + 1, base_zoom, zoom_levels)
    image_bl = downsample(base_dir, (tile[0] * 2, tile[1] * 2 + 1), zoom + 1, base_zoom, zoom_levels)
    image_br = downsample(base_dir, (tile[0] * 2 + 1, tile[1] * 2 + 1), zoom + 1, base_zoom, zoom_levels)

    if image_tl is _blank_image and\
       image_tr is _blank_image and\
       image_bl is _blank_image and \
       image_br is _blank_image:
        #print("return empty: {1}/{2}".format(base_dir, zoom, tile, base_zoom))
        return _blank_image

    print("downsample: {0}/{1}-{2} until {3}".format(base_dir, zoom, tile, base_zoom))
    new_img = merge(image_tl, image_tr, image_bl, image_br)

    if not os.path.exists(result_dir):
        logger.debug("create directory: {0}".format(result_dir))
        os.makedirs(result_dir)

    if zoom in zoom_levels:
        new_img.save(result_filename, "PNG")

    return new_img


def start_downsampling(base_dir, base_zoom, zoom_levels):
    for x in range(2 ** zoom_levels[0]):
        for y in range(2 ** zoom_levels[0]):
            downsample(base_dir, (x, y), zoom_levels[0], base_zoom, zoom_levels)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('dir', help='directory where we want to calculate the zoom levels', action='store')
    parser.add_argument('basic_zoom', type=int, help='zoom level our calculations are based')
    parser.add_argument('-z', dest='zoomlevel', nargs='+', type=check_zoom_level,  default=None, help='zoom levels to render (default 0-12)')
    #parser.add_argument('-y', dest='threads', type=check_thread_count, default=1, help='number of threads')
    parser.add_argument('-v', '--verbose', help='show extra information', action='store_true')
    parser.add_argument('-d', '--debug', help='show debug informations', action='store_true')
    # parser.add_argument('--gpu', help='run downsample algorihm using gpu', action='store_true')
    # TODO: delete old tiles of outputdir (if they are not going to be overwritten)

    args = parser.parse_args()

    if args.zoomlevel is None:
        args.zoomlevel = [range(0, args.basic_zoom)]

    if args.verbose:
        logger.setLevel(logging.INFO)

    if args.debug:
        logger.setLevel(logging.DEBUG)

    if not os.path.exists(args.dir):
        print("directory does not exist: {0}".format(args.dir))
        sys.exit(1)

    if not os.path.exists(os.path.join(args.dir, str(args.basic_zoom))):
        print("directory for zoom level {0} does not exist".format(args.basic_zoom))
        sys.exit(1)

    # parse list of zoom levels we want to render
    zoom_levels_set = set()
    for level in args.zoomlevel:
        zoom_levels_set.update(level)
    zoom_levels = sorted(zoom_levels_set)

    if zoom_levels[-1] >= args.basic_zoom:
        print("we can only downsample images")
        sys.exit(1)

    print("parse zoomlevels: {0}".format(zoom_levels))

    start_downsampling(args.dir, args.basic_zoom, zoom_levels)
