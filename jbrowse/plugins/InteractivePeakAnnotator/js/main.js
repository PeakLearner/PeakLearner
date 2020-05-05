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
            var browser = this.browser
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
                  var storeConf = {
                     browser: browser,
                     refSeq: browser.refSeq,
                     type: 'MultiBigWig/Store/SeqFeature/MultiBigWig'
                     //... the new storeclass config for the bigwigs....
                  };
                var storeName = browser.addStoreConfig(null, storeConf);

                var trackConf = Object.assign(this.config, {
                    store: storeName
                    })
                browser.publish('/jbrowse/v1/v/tracks/replace', [trackConf]);
                //sendPost(labelsJSON);
                }
            });
        }
    });
});
