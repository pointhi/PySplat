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

try:
    import pyopencl as cl
    import numpy
    cl_support = True
except ImportError:
    cl_support = False


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

        print("submit tile: \"{0}\" using {1} source tiles".format(destination, len(sources)))
        self._executor.submit(self.merge_images, sources, destination)

    def wait_until_empty(self):
        while not self._executor._work_queue.empty():
            time.sleep(.01)

    def merge_images(self, sources, destination):
        print("calculate tile: \"{0}\" using {1}".format(destination, sources))
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

        return destination_image


class OpenCLTileMerger(TileMerger):
    def __init__(self, image_order, threads):
        TileMerger.__init__(self, image_order, threads)

        # create opencl code to compare vectors
        # TODO: improve code in a way so we need to compare specific values only once
        self.pix_pos_compare_code = ""
        for i in range(len(image_order)):
            x, y, z, w = image_order[i]
            self.pix_pos_compare_code += "if(pix.x == (uint){x} && pix.y == (uint){y} && pix.z == (uint){z} && pix.w == (uint){w}) {{ return {i}; }}\nelse ".format(
                x=x, y=y, z=z, w=w, i=i)
        self.pix_pos_compare_code += "{ return -1; }\n"

        # initialize OpenCL
        self.ctx = cl.create_some_context(interactive = False)
        self.queue = cl.CommandQueue(self.ctx)
        self.prg = self._build_cl_program()

    def _build_cl_program(self):
        # load and build OpenCL function
        return cl.Program(self.ctx, '''//CL//
                bool equal_uint4(uint4 pix1, uint4 pix2) {
                    if(pix1.x == pix2.x && pix1.y == pix2.y && pix1.z == pix2.z && pix1.w == pix2.w) {
                        return 1;
                    } else {
                        return 0;
                    }
                }

                int pix_pos(uint4 pix) {
                ''' + self.pix_pos_compare_code + '''
                }

                __kernel void convert(
                    read_only image2d_t src1,
                    read_only image2d_t src2,
                    write_only image2d_t dest
                )
                {
                    const sampler_t sampler =  CLK_NORMALIZED_COORDS_FALSE | CLK_ADDRESS_CLAMP_TO_EDGE | CLK_FILTER_NEAREST;
                    int2 pos = (int2)(get_global_id(0), get_global_id(1));

                    uint4 pix1 = read_imageui(src1, sampler, pos);
                    uint4 pix2 = read_imageui(src2, sampler, pos);

                    uint4 pix;

                    if(equal_uint4(pix2, (uint4)((uint)255, (uint)255, (uint)255, (uint)0))) {
                        pix = pix1;
                    } else {
                        int pix1_pos = pix_pos(pix1);
                        int pix2_pos = pix_pos(pix2);

                        if(pix1_pos == -1) {
                            pix = pix2;
                        } else if(pix2_pos == -1) {
                            pix = pix1;
                        } else if(pix1_pos < pix2_pos) {
                            pix = pix1;
                        } else {
                            pix = pix2;
                        }
                    }

                    write_imageui(dest, pos, pix);
                }
                ''').build()

    def merge_loaded_images(self, source_images):
        converted_images = []
        source_array = []
        source_buffer = []
        for single_source in source_images:
            new_image = single_source.convert('RGBA')
            converted_images += [new_image]
            new_numpy_array = numpy.array(new_image)
            source_array += [new_numpy_array]
            source_buffer += [cl.image_from_array(self.ctx, new_numpy_array, 4)]

        # get size of source image (note height is stored at index 0)
        h = source_array[0].shape[0]
        w = source_array[0].shape[1]

        # build destination OpenCL Image
        fmt = cl.ImageFormat(cl.channel_order.RGBA, cl.channel_type.UNSIGNED_INT8)
        dest_buf = cl.Image(self.ctx, cl.mem_flags.READ_WRITE, fmt, shape=(w, h))

        # execute OpenCL function
        self.prg.convert(self.queue, (w, h), None, source_buffer[0], source_buffer[1], dest_buf)

        if len(source_images) > 2:
            source_buffer[0].release()
            source_buffer[1].release()
            for i in range(2, len(source_images)):
                # execute OpenCL function
                self.prg.convert(self.queue, (w, h), None, source_buffer[i], dest_buf, dest_buf)
                source_buffer[i].release()

        # copy result back to host
        dest = numpy.empty_like(source_array[0])
        cl.enqueue_copy(self.queue, dest, dest_buf, origin=(0, 0), region=(w, h)).wait()
        dest_buf.release()  # memory release useful or even required?


        # convert image and save it
        return Image.fromarray(dest)



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

    if args.gpu:
        if not cl_support:
            print("This system doesn't support GPU Acceleration yet! Please install the required packages")
            sys.exit(1)
        tile_merger = OpenCLTileMerger(image_order, args.threads)
    else:
        tile_merger = TileMerger(image_order, args.threads)



    print("input dirs: {0}".format(args.inputdirs))
    print("output dir: {0}".format(output_dir))
    print("scf data: {0}".format(scf_data))

    merge_maps(args.inputdirs, output_dir, tile_merger)

    tile_merger.wait_until_empty()