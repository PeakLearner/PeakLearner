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
                if (data.length) {
                    localStorage.setItem('highlightFlag', 1);
                    const region = data[0];
                    const regions = JSON.parse(localStorage.getItem('ipaFeatures') || '[]');
                    regions.push(region);
                    localStorage.setItem('ipaFeatures', JSON.stringify(regions));
                    //args.browser.clearHighlight();
                }
                else
                {
                  localStorage.setItem('highlightFlag', 0);
                  var labelsJSON = JSON.parse(localStorage.getItem('ipaFeatures'));
                  console.log("sending new labels: ", labelsJSON[labelsJSON.length - 1]);
                  //sendPost(labeslJSON);
                }
            });
        }
    });
});
