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
    return declare([ XYPlot],
        {
            _defaultConfig: function () {
                return Util.deepUpdate(dojo.clone(this.inherited(arguments)),
                    {
                        onHighlightClick: function (feature, track) {
                            // grab known labels and
                            let features = JSON.parse(localStorage.getItem('ipaFeatures'));
                            // eslint-disable-next-line radix
                            const highlightFlag = parseInt(localStorage.getItem('highlightFlag'));
                            // uses highlightFlag to determine if editing or removing
                            if (highlightFlag === 1) {
                                // this is wear we define the types of labels, to create a new kind of
                                // label add to this list and the two down below for determining the color
                                const states = ['unknown', 'peak', 'nopeak', 'peakStart', 'peakEnd'];
                                // loops through known labels for the label clicked
                                features.forEach(f => {
                                    if (f.ref === feature.get('ref') &&
                               f.start === feature.get('start') &&
                               f.end === feature.get('end')) {
                                        if (f[track.name]) {
                                            // increments the track type
                                            f[track.name] = (f[track.name] + 1) % states.length;
                                        } else {
                                            // if the track has no type set to "Peak"
                                            f[track.name] = 1;
                                        }
                                    }
                                });
                            } else {
                                // loop through labels removing clicked one
                                // eslint-disable-next-line consistent-return
                                features = features.filter(function (f) {
                                    if (f.start !== feature.get('start')) {
                                        return f;
                                    }
                                });
                                // json of information of removed label
                                var removeJSON = {
                                    'name': track.name,
                                    'ref': feature.get('ref'),
                                    'start': feature.get('start'),
                                    'end': feature.get('end')
                                };
                                // eslint-disable-next-line no-undef
                                sendPost('remove', removeJSON);
                            }
                            // redraw to update model
                            track.redraw();
                            localStorage.setItem('ipaFeatures', JSON.stringify(features));
                        },

                        highlightColor: function (feature, track) {
                            // determins the color of the see through part of the label
                            // to add new type of label add type to this list
                            const states = {
                                0: 'rgba(100,100,100,.4)',
                                1: '#0f05',
                                2: '#ff05',
                                3: 'rgba(255,0,0,0.4)',
                                4: 'rgba(255,150,0,0.4)'
                            };
                            return states[feature.data[track.name] || 0];
                        },

                        indicatorColor: function (feature, track) {
                            // determins the color of the bar at the bottom of the label
                            // to add new type of label add type to this list
                            const states = {0: '#f00', 1: '#0f0', 2: '#ff0', 3: '#d3034f', 4: '#d30303'};
                            return states[feature.data[track.name] || 0];
                        }
                    });
            }
        });
});
