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
import math

sys.path.append(os.path.join(sys.path[0], "../")) # enable package import from parent directory

from PySplat.util.argparse_helper import check_thread_count, check_zoom_level
from PySplat.util.geo_file import parse_geo_file
from PySplat.util.slippy_map_math import deg2num, num2deg


# use xrange on python2 (for speed reasons)
try:
    xrange
except NameError:
    xrange = range


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def get_pixel_from_pos(rf_geo_data, lat, lon):
    lon_per_pixel = math.fabs((rf_geo_data['bb'][1][1]-rf_geo_data['bb'][0][1])/rf_geo_data['imagesize'][1])
    lat_per_pixel = math.fabs((rf_geo_data['bb'][1][0]-rf_geo_data['bb'][0][0])/rf_geo_data['imagesize'][0])

    pixel_x = int((lon-rf_geo_data['bb'][0][1])/lon_per_pixel)
    pixel_y = int((rf_geo_data['bb'][0][0]-lat)/lat_per_pixel)

    return (pixel_x, pixel_y)


def create_tile(xtile, ytile, base_path, zoom, rf_img, rf_geo_data, **kwargs):
    (lat_deg_start, lon_deg_start) = num2deg(xtile, ytile, zoom)
    (lat_deg_end, lon_deg_end) = num2deg(xtile+1, ytile+1, zoom)

    result_dir = os.path.join(base_path, str(zoom), str(xtile))
    result_filename = os.path.join(result_dir, "{0}.png".format(ytile))

    lat_per_pixel = math.fabs((rf_geo_data['bb'][1][0]-rf_geo_data['bb'][0][0])/rf_geo_data['imagesize'][0])
    lon_per_pixel = math.fabs((rf_geo_data['bb'][1][1]-rf_geo_data['bb'][0][1])/rf_geo_data['imagesize'][1])

    (start_pixel_x, start_pixel_y) = get_pixel_from_pos(rf_geo_data, lat_deg_start, lon_deg_start)
    (end_pixel_x, end_pixel_y) = get_pixel_from_pos(rf_geo_data, lat_deg_end, lon_deg_end)

    print("use pixel: {0}|{1} to {2}|{3}".format(start_pixel_x, start_pixel_y, end_pixel_x, end_pixel_y))

    # TODO: refactor to use OpenCL
    #source_img = ImageChops.offset(rf_img,start_pixel_x, start_pixel_y)
    source_img = rf_img.transform((256,256),Image.EXTENT, (start_pixel_x, start_pixel_y, end_pixel_x, end_pixel_y))
    source_img = source_img.resize((256,256))

    source_img = source_img.convert('RGBA')

    #https://stackoverflow.com/questions/765736/using-pil-to-make-all-white-pixels-transparent
    pixdata = source_img.load()
    for y in xrange(source_img.size[1]):
        for x in xrange(source_img.size[0]):
            if pixdata[x, y] == (255, 255, 255, 255):
                pixdata[x, y] = (255, 255, 255, 0) # white to transparent
            elif pixdata[x, y] == (0, 0, 0, 255):
                pixdata[x, y] = (255, 255, 255, 0) # black to transparent

    if kwargs.get('blank_tiles') is not True and source_img.convert("L").getextrema() == (255, 255):
        print("skip tile: {0}".format(result_filename))
        return

    if not os.path.exists(result_dir):
        logger.debug("create directory: {0}".format(result_dir))
        os.makedirs(result_dir)

    print("create tile: {0}".format(result_filename))

    # save tile
    source_img.save(result_filename, "PNG")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('inputfile', help='image file which should be converted', action='store')
    parser.add_argument('outputdir', help='output directory where we store the calculated tiles')
    parser.add_argument('-z', dest='zoomlevel', nargs='+', type=check_zoom_level,  default=[range(0, 12 + 1)], help='zoom levels to render (default 0-12)')
    parser.add_argument('--including-blank-tiles', help='also write blank tiles', action='store_true')
    parser.add_argument('-y', dest='threads', type=check_thread_count, default=1, help='number of threads')
    parser.add_argument('-v', '--verbose', help='show extra information', action='store_true')
    parser.add_argument('-d', '--debug', help='show debug informations', action='store_true')
    # TODO: delete old tiles of outputdir (if they are not going to be overwritten)

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)

    if args.debug:
        logger.setLevel(logging.DEBUG)

    ppm_file = args.inputfile
    geo_file = os.path.splitext(ppm_file)[0] + ".geo"

    if not os.path.isfile(ppm_file):
        logger.error(".ppm file not found: \"{file}\"".format(file=ppm_file))
        sys.exit(1)

    ppm_file_parsed = Image.open(ppm_file)

    if not os.path.isfile(geo_file):
        logger.error(".geo file not found: \"{file}\" (required for geo referencing)".format(file=geo_file))
        sys.exit(1)

    geo_file_parsed = parse_geo_file(geo_file)

    output_dir = args.outputdir

    # TODO: not really required, becaue we create all directories later
    if not os.path.exists(output_dir):
        print("create directory: {0}".format(output_dir))
        os.makedirs(output_dir)

    # parse list of zoom levels we want to render
    zoom_levels_set = set()
    for level in args.zoomlevel:
        zoom_levels_set.update(level)
    zoom_levels = sorted(zoom_levels_set)

    print("Load image: {0}".format(ppm_file))
    print("geo file: {0}".format(geo_file))
    print("Store tiles into: {0}".format(args.outputdir))
    print("levels: {0}".format(zoom_levels))

    for zoom in zoom_levels:
        (xtile_start, ytile_start) = deg2num(geo_file_parsed['bb'][0][0], geo_file_parsed['bb'][0][1], zoom)
        (xtile_end, ytile_end) = deg2num(geo_file_parsed['bb'][1][0], geo_file_parsed['bb'][1][1], zoom)

        print("generate tiles from {xtile_start}/{ytile_start} to {xtile_end}/{ytile_end} for zoom level {zoom}".format(
            xtile_start=xtile_start
            , ytile_start=ytile_start
            , xtile_end=xtile_end
            , ytile_end=ytile_end
            , zoom=zoom))

        # TODO: -180 +180 overflow
        for xtile in range(xtile_start, xtile_end + 1):
            for ytile in range(ytile_start, ytile_end + 1):
                create_tile(xtile, ytile, output_dir, zoom, ppm_file_parsed, geo_file_parsed, blank_tiles=args.including_blank_tiles)
