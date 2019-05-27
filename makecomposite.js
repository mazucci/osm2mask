var moyale = ee.ImageCollection('users/mayzurb/moyale');
//  .select(['b3', 'b2', 'b1']);

// Temporally composite the images with a maximum value function.
var composite = moyale.max();

var region = ee.Geometry.Rectangle([38.9460,3.3067, 39.1492,3.5463]);

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
    gamma: [1.3, 1.3, 1.3]
  
};

Map.setCenter(38.938,3.466);
Map.addLayer(composite, vizParams, 'composite');

var visualization = composite.visualize(vizParams);

// Create a task that you can launch from the Tasks tab.
Export.image.toDrive({
  image: visualization,
  description: 'composite',
  scale: 3,
  maxPixels: 2e9

});
