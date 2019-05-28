// bounds
var region = ee.Geometry.Rectangle([39.3519,	3.2814, 39.5174,	3.3821]);

var collection = ee.ImageCollection('users/mayzurb/butetown');

// Temporally composite the images with a maximum value function.
var composite = collection.max();

//calculate viz params
var minmax = composite.reduceRegion({
  reducer: ee.Reducer.minMax(),
  geometry: region,
  scale: 20
});

var stats = minmax.getInfo();

var vizParams = {bands: ['b3', 'b2', 'b1'],
    max: [stats['b3_max'], stats['b2_max'], stats['b1_max']],
    min: [stats['b3_min'], stats['b2_min'], stats['b1_min']],
    gamma: [1.5, 1.3, 1.3],
  
};

var clipped = composite.clip(region);

Map.setCenter(38.938,3.466);
Map.addLayer(clipped, vizParams, 'composite');

var visualization = composite.visualize(vizParams);

// Create a task that you can launch from the Tasks tab.
Export.image.toDrive({
  image: visualization,
  description: 'composite',
  region: region,
  scale: 3,
  maxPixels: 2e9

});
