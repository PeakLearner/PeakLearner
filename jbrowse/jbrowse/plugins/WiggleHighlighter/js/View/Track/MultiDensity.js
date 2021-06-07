try {
  define([
    'dojo/_base/declare',
    'MultiBigWig/View/Track/MultiWiggle/MultiDensity',
    './Base',
  ], function (declare, Density, Base) {
    return declare([Density, Base], {})
  })
} catch (e) {}
