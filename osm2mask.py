import math
import processing
from PyQt4.QtCore import *

# set your working directory
work_dir = '/home/may/foss4glocal/'

def osm2mask(road_layer_name, sat_layer_name, bbox, scale):
    """ road_layer_name: the name of the layer that contains roads from osm.
        bbox: a list containing the coordinates for the bounding box of the AOI.
        scale: the scale of the image to use e.g. (1, 3, 10, 20, 30)m
    """
    # creates a point layer
    layer = QgsVectorLayer('Point?crs=epsg:4326', 'point', 'memory')
    
    # set the provider
    prov = layer.dataProvider()
    point1 = QgsPoint(bbox[0], bbox[1])
    point2 = QgsPoint(bbox[2], bbox[3])
    
    # add a new feature and assign the geometry
    feat1 = QgsFeature()
    feat1.setGeometry(QgsGeometry.fromPoint(point1))
    feat2 = QgsFeature()
    feat2.setGeometry(QgsGeometry.fromPoint(point2))
    prov.addFeatures([feat1, feat2])
    
    # update layer extent
    layer.updateExtents()
    
    # add the layer to the Layers panel
    QgsMapLayerRegistry.instance().addMapLayers([layer])
    
    # get bounding box
    processing.runandload('qgis:polygonfromlayerextent', layer, False, "memory:bbox")
    bbox_layer = QgsMapLayerRegistry.instance().mapLayersByName("Extent")[0]
    
    for lyr in QgsMapLayerRegistry.instance().mapLayers().values():
        if lyr.name() == road_layer_name:
            layer = lyr
            break
            
    
    # clip road layer to bbox extent
    processing.runalg('qgis:clip', layer, bbox_layer, '/home/may/foss4glocal/clipped.shp')
    clipped = QgsVectorLayer(work_dir+'clipped.shp', 'clipped', 'ogr')
    
    # reproject layer to work with meters
    processing.runalg('qgis:reprojectlayer', clipped, 'EPSG:3857', '/home/may/foss4glocal/clipped_merc.shp')
    clipped = QgsVectorLayer(work_dir+'clipped_merc.shp', 'clipped_merc', 'ogr')
    # select wider highways
    query = "(lower(\"highway\")=lower('trunk')) \
    OR (lower(\"highway\")=lower('primary')) \
    OR (lower(\"highway\")=lower('secondary')) \
    OR (lower(\"highway\")=lower('tertiary'))"
    
    selection = clipped.getFeatures(QgsFeatureRequest().setFilterExpression(query))
    clipped.setSelectedFeatures([k.id() for k in selection])
    
    # save layer with selected features
    QgsVectorFileWriter.writeAsVectorFormat(clipped, work_dir+'main_roads.shp', "utf-8", clipped.crs(), "ESRI Shapefile", 1)
    main_roads = QgsVectorLayer(work_dir+'main_roads.shp', 'main_roads', 'ogr')
    
    # select minor roads
    clipped.invertSelection()
    
    # save minor roads layer
    QgsVectorFileWriter.writeAsVectorFormat(clipped, work_dir+'minor_roads.shp', "utf-8", clipped.crs(), "ESRI Shapefile", 1)
    minor_roads = QgsVectorLayer(work_dir+'minor_roads.shp', 'minor_roads', 'ogr')
    
    # buffer around main roads layer
    processing.runalg('qgis:fixeddistancebuffer', main_roads, 5, 5, False, work_dir+'main_roads_buff.shp')
    main_roads_buff = QgsVectorLayer(work_dir+'main_roads_buff.shp', 'main_roads_buff', 'ogr')
    # buffer around minor roads layer
    processing.runalg('qgis:fixeddistancebuffer', minor_roads, 3, 5, False, work_dir+'minor_roads_buff.shp')
    minor_roads_buff = QgsVectorLayer(work_dir+'minor_roads_buff.shp', 'minor_roads_buff', 'ogr')
    # merge both buffered roads
    processing.runalg('qgis:mergevectorlayers', [main_roads_buff ,  minor_roads_buff], work_dir+'roads_buff.shp')
    roads_buff = QgsVectorLayer(work_dir+'roads_buff.shp', 'roads_buff', 'ogr')
    # add is_road field
    roads_buff.startEditing()
    res = roads_buff.dataProvider().addAttributes([QgsField("is_road", QVariant.Int)])
    is_roadidx = roads_buff.dataProvider().fieldNameIndex("is_road")
    roads_buff.commitChanges()
    # set is_road to 1 for all features
    roads_buff.startEditing()
    for feat in roads_buff.getFeatures():
        feat.setAttribute(is_roadidx, 1)
        roads_buff.updateFeature(feat)
    roads_buff.commitChanges()
    
    processing.runalg('qgis:reprojectlayer', bbox_layer, 'EPSG:3857', work_dir+'bbox_merc.shp')
    bbox_merc = QgsVectorLayer(work_dir+'bbox_merc.shp', 'bbox_merc', 'ogr')
    ext = bbox_merc.extent()

    # create raster
    processing.runandload('gdalogr:rasterize', \
    {
     'INPUT': roads_buff,
     'FIELD': "is_road",
     'DIMENSIONS': 1,
     'WIDTH': math.sqrt(scale),
     'HEIGHT': math.sqrt(scale),
     'RAST_EXT': "%s,%s,%s,%s" % (ext.xMinimum(), ext.xMaximum(), ext.yMinimum(), ext.yMaximum()),
     'NO_DATA': 0,
     'BIGTIFF': 2,
     'OUTPUT': work_dir + 'roads_raster.tif'
    })
    
    # save rendered raster
    roads_raster = QgsMapLayerRegistry.instance().mapLayersByName("Rasterized")[0]
    provider = roads_raster.dataProvider()
    # adjust min and max values for black and white
    grayrenderer = QgsSingleBandGrayRenderer(provider, 1)
    roads_raster.setRenderer(grayrenderer)
    renderer = roads_raster.renderer()
    uses_band = renderer.usesBands()
    myType = renderer.dataType(uses_band[0])
    myEnhancement = QgsContrastEnhancement(myType)
    contrast_enhancement = QgsContrastEnhancement.StretchToMinimumMaximum
    myEnhancement.setContrastEnhancementAlgorithm(contrast_enhancement, True)
    myEnhancement.setMinimumValue(0)
    myEnhancement.setMaximumValue(1)
    roads_raster.renderer().setContrastEnhancement(myEnhancement)
    # write rendered raster
    pipe = QgsRasterPipe()
    pipe.set(provider.clone())
    pipe.set(renderer.clone())
    file_writer = QgsRasterFileWriter(work_dir+'rend_roads_raster.tif')
    file_writer.writeRaster(pipe, roads_raster.width(), roads_raster.height(),roads_raster.extent(), roads_raster.crs())
    
    # create tiles for mask
    processing.runalg('gdalogr:gdal2tiles',\
    {
     'INPUT': work_dir + 'rend_roads_raster.tif',
     'PROFILE': 0,
     'ZOOM': 16,
     'OUTPUTDIR': work_dir + 'mask_tiles/'
    })
    
    composite = QgsMapLayerRegistry.instance().mapLayersByName(sat_layer_name)[0]
    if composite.crs() != roads_raster.crs():
        processing.runandload('gdalogr:warpreproject',
        {
         'INPUT': composite,
         'SOURCE_SRS': str(composite.crs().authid()),
         'DEST_SRS': 'EPSG:3857',
         'METHOD': 0,
         'USE_RASTER_EXTENT': True,
         'RTYPE': 5,
         'BIGTIFF': 2,
         'OUTPUT': work_dir+sat_layer_name+'_merc.tif'
         
        })
        composite2 = QgsMapLayerRegistry.instance().mapLayersByName("Reprojected")[0]
        # keep style
        iface.setActiveLayer(composite)
        iface.actionCopyLayerStyle().trigger()
        iface.setActiveLayer(composite2)
        iface.actionPasteLayerStyle().trigger()
        pipe = QgsRasterPipe()
        pipe.set(composite2.dataProvider().clone())
        pipe.set(composite2.renderer().clone())
        file_writer = QgsRasterFileWriter(work_dir+'rend_composite_raster.tif')
        file_writer.writeRaster(pipe, composite2.width(), composite2.height(),composite2.extent(), composite2.crs())
        
        comp_for_tiles = QgsRasterLayer(work_dir+'rend_composite_raster.tif', 'rend_composite_raster.tif')
    else:
        comp_for_tiles = composite
    # create tiles for composite
    processing.runalg('gdalogr:gdal2tiles',\
    {
     'INPUT': comp_for_tiles,
     'PROFILE': 0,
     'ZOOM': 16,
     'OUTPUTDIR': work_dir + 'sat_tiles/'
    })
    
    print "done"
    
osm2mask("roads", "composite", [39.3519, 3.2814, 39.5174, 3.3821], 3.0)