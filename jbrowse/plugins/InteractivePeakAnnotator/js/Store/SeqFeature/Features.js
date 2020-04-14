define([
    'dojo/_base/declare',
    'JBrowse/Model/SimpleFeature',
    'JBrowse/Store/SeqFeature'
],
function (
    declare,
    SimpleFeature,
    SeqFeatureStore,
) {
    return declare([ SeqFeatureStore ], {
        getFeatures(query, featureCallback, finishedCallback) {
            var features = localStorage.getItem('ipaFeatures');
            if (features) {
                features = JSON.parse(features);
                features.forEach(data => {
                    featureCallback(new SimpleFeature({ data }));
                });
                finishedCallback();
            }
        },

        saveStore() {
            return {
                urlTemplate: this.config.blob.url
            };
        }

    });
});
