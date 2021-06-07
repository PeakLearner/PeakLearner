try {
  define([
    'dojo/_base/declare',
    'WiggleHighlighter/View/Track/MultiXYPlot',
    './Base',
  ], function (declare, XYPlot, Base) {
    return declare([XYPlot, Base], {})
  })
} catch (e) {}
