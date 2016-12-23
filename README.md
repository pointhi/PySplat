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
* (opencl, PIL,..)
