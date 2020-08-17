define([
    'dojo/_base/declare',
    'JBrowse/Plugin'
],
function (
    declare,
    JBrowsePlugin
) {
    return declare(JBrowsePlugin, {
        // eslint-disable-next-line no-unused-vars
        constructor: function (args) {
            console.log('InteractivePeakAnnotator plugin starting');
            // set up listiner for the globalHighlightChanged event
            // data is either a list of highlights or an empty list
            dojo.subscribe('/jbrowse/v1/n/globalHighlightChanged', function (data) {
                if (data.length) {
                    // flag set to editing
                    localStorage.setItem('highlightFlag', 1);
                    // add new highlight to storage
                    const region = data[0];
                    const regions = JSON.parse(localStorage.getItem('ipaFeatures') || '[]');
                    regions.push(region);
                    localStorage.setItem('ipaFeatures', JSON.stringify(regions));
                } else {
                    // flag set to removing
                    localStorage.setItem('highlightFlag', 0);
                    // grab labels and send to server
                    var labelsJSON = JSON.parse(localStorage.getItem('ipaFeatures'));
                    console.log('sending new labels: ', labelsJSON[labelsJSON.length - 1]);
                    // eslint-disable-next-line no-undef
                    sendPost('save', labelsJSON);
                }
            });
        }
    });
});
