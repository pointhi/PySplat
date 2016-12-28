## PySplat

Doing RF calculations using python and [SPLAT](http://www.qsl.net/kd2bd/splat.html)

This project aims for a specific usecase, means calculation of Signal Propagation maps for the usage on online maps.

Means we call SPLAT in a specific way so we have a georeferenced result. This the can be split into tiles which are
usable as overlay tiles for libraries like [Leaflet](http://leafletjs.com). Those tiles can furthermore be processed by
merging multiple of those maps into a single one. Using those techniques allows us to creating maps showing the overal
coverage of radio transmitters with as many TX-sites as we want (without having the limitations of SPLAT).

### Features

* Calculation of specific SPLAT-Maps
* Split SPLAT-Maps into Tiles
* Merging of those Tiles into a single one

### Dependencies

* splat

python dependencies located in ```requirements.txt`

### Example usage

#### Calculate basic RF map

*(currently, you have to download and preprocess the required srtm files manually)*

```
./PySplat/pysplat.py example/qth/OE5XGL.qth --out ./example/html/base --srtm ./path/to/srtm/folder
```

#### Split tiles

```
./PySplat/pysplat_split.py ./example/html/base/OE5XGL.ppm ./example/html/rendered/OE5XGL -z 1-12
```

Now we can open the leaflet map located in ```./example/html/map.html``` and check out our new rendered RF map overlay.

#### Merge multiple tiles

```
./PySplat/pysplat_merge.py ./example/html/rendered/OE5*/ --out ./example/html/rendered_merged/OE5xxx --gpu
```

*Please note, using the ```--gpu``` flag activates the OpenCL implementation, which is highly recommended.
Even using OpenCL over CPU is more than 10 times faster compared to the native python implementation.*