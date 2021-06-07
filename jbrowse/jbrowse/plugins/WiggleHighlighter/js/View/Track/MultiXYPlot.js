try {
  define([
    'dojo/_base/declare',
    'MultiBigWig/View/Track/MultiWiggle/MultiXYPlot',
    './Base',
  ], function (declare, XYPlot, Base) {
    return declare([XYPlot, Base], {})
  })
} catch (e) {}
