define([
    'dojo/_base/declare',
    'JBrowse/Util',
    'WiggleHighlighter/View/Track/MultiXYPlot'
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
                    var states = ['unknown', 'peak', 'nopeak'];
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
                    var states = {0: '#f005', 1: '#0f05', 2: '#ff05'};
                    return states[feature.get(track.name) || 0];
                },
                indicatorColor: function (feature, track) {
                    var states = {0: '#f00', 1: '#0f0', 2: '#ff0'};
                    return states[feature.get(track.name) || 0];
                }
            });
        }
    });
});
