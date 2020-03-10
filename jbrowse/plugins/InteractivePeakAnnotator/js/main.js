define([
    'dojo/_base/declare',
    'JBrowse/Plugin'
],
function (
    declare,
    JBrowsePlugin
) {
    return declare(JBrowsePlugin, {
        constructor: function (args) {
            console.log('InteractivePeakAnnotator plugin starting');
            dojo.subscribe('/jbrowse/v1/n/globalHighlightChanged', function (data) {
                console.log(data);
                if (data.length) {
                    const region = data[0];
                    const regions = JSON.parse(localStorage.getItem('ipaFeatures') || '[]');
                    regions.push(region);
                    localStorage.setItem('ipaFeatures', JSON.stringify(regions));
                    args.browser.clearHighlight();
                }
            });
        }
    });
});
