define([
    'dojo/_base/declare',
    'JBrowse/Util',
    'WiggleHighlighter/View/Track/XYPlot'
],
function (
    declare,
    Util,
    XYPlot
) {
    return declare([ XYPlot], {
        _defaultConfig: function () {
            return Util.deepUpdate(dojo.clone(this.inherited(arguments)), {
                onHighlightClick: function (feature, track) {
                    var features = JSON.parse(localStorage.getItem('ipaFeatures'));
                    var states = ['unknown', 'peak', 'nopeak', 'peakStart', 'peakEnd'];
                    features.forEach(f => {
                        if (f.ref === feature.get('ref') &&
                            f.start === feature.get('start') &&
                            f.end === feature.get('end')
                        ) {
                            if (f[track.name]) {
                                f[track.name] = (f[track.name] + 1) % states.length;
                            } else {
                                f[track.name] = 1;
                            }
                        }
                    });
                    localStorage.setItem('ipaFeatures', JSON.stringify(features));
                    track.redraw();
                },
                highlightColor: function (feature, track) {
                    // determins the color of the see through part of the label
                    // to add new type of label add type to this list
                    var states = {0: 'rgba(100,100,100,.4)', 1: '#0f05', 2: '#ff05', 3: 'rgba(255,0,0,0.4)', 4: 'rgba(255,150,0,0.4)'};
                    return states[feature.data[track.name] || 0];
                },

                indicatorColor: function (feature, track) {
                    // determins the color of the bar at the bottom of the label
                    // to add new type of label add type to this list
                    var states = {0: '#f00', 1: '#0f0', 2: '#ff0', 3: '#d3034f', 4: '#d30303'};
                    return states[feature.data[track.name] || 0];
                }
            });
        }
    });
});
