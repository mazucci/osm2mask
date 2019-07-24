# osm2mask
Creates raster masks for road extraction with Machine Learning from osm data

## How to use:

1. Create a composite from the rasters you want to use. For this, you can use the makecomposite.js file which is a Google Earth Engine script that generates a composite delimited to a bounding box from a GEE asset or collection ready for download.
2. Download the corresponding/overlaping OpenStreetMap roads for the bounding box of your composite. Use query.txt file for generating the [overpass](https://overpass-turbo.eu/) query. Make sure to use the same bounding box!
3. Open QGIS and load both layers, the composite and the roads. Set the parameters of the osm2mask.py script according to the layers name and resolution and run. This will generate some files and two directories, one with tiles from the composite and one with tiles from the mask, these will serve as input for training a machine learning model. You can play with the resolution for gdal2tiles to increase or decrease the quality of the images generated.
