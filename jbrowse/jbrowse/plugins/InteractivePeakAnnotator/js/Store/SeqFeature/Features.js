define([
    'dojo/_base/declare',
    'dojo/_base/lang',
    'dojo/_base/array',
    'dojo/io-query',
    'dojo/request',
    'dojo/Deferred',
    'JBrowse/Util',
    'JBrowse/Model/SimpleFeature',
    'JBrowse/Store/SeqFeature'
],
function (
    declare,
    lang,
    array,
    ioquery,
    dojoRequest,
    Deferred,
    Util,
    SimpleFeature,
    SeqFeatureStore,
) {
    return declare([ SeqFeatureStore ], {
        getFeatures(query, featureCallback, finishedCallback, errorCallback) {

            var features = localStorage.getItem(this.config.label);
            if(features)
            {
                features = JSON.parse(features);
                features.forEach(data => {
                   featureCallback(new SimpleFeature({data}))
                });
            }
        },
        addFeature: function(query, callback){
            var features = JSON.parse(localStorage.getItem(this.config.label) || '[]');

            features.push(query);

            localStorage.setItem(this.config.label, JSON.stringify(features));

            callback()
        },
        updateFeature(query, callback)
        {
            var features = JSON.parse(localStorage.getItem(this.config.label));

            features = features.filter(function(f)
            {
                //If it isn't the value we are looking for
                if(f.start === query['start'] && f.ref === query['ref'] && f.end === query['end'])
                {
                    f.label = query['label'];

                    return f;
                }
                return f;
            });

            localStorage.setItem(this.config.label, JSON.stringify(features))

            callback()
        },
        updateAlignedFeatures(query, callback)
        {
            let currentStore = this.config.storeClass;

            this.browser.view.tracks.forEach(track => {
                if(track.config.storeConf)
                {
                    if(track.config.storeConf.storeClass === currentStore)
                    {
                        let trackFeatures = JSON.parse(localStorage.getItem(track.config.label))

                        let outputFeatures = trackFeatures.filter(function(f)
                        {
                            //If it isn't the value we are looking for
                            if(f.start === query['start'] && f.ref === query['ref'] && f.end === query['end'])
                            {
                                f.label = query['label'];

                                return f;
                            }
                            return f;
                        });

                        localStorage.setItem(track.config.label, JSON.stringify(outputFeatures))
                    }
                }
            })
            callback();
        },
        removeFeature(query, callback)
        {
            var features = JSON.parse(localStorage.getItem(this.config.label));

            features = features.filter(function(f)
            {
                //If it isn't the value we are looking for
               if(f.start !== query['start'] || f.ref !== query['ref'] || f.end !== query['end'])
               {
                   return f;
               }
            });

            localStorage.setItem(this.config.label, JSON.stringify(features))

            callback()
        },
        removeAlignedFeatures(query, callback)
        {
            let currentStore = this.config.storeClass;

            this.browser.view.tracks.forEach(track => {
                if(track.config.storeConf)
                {
                    if (track.config.storeConf.storeClass === currentStore)
                    {
                        let trackFeatures = JSON.parse(localStorage.getItem(track.config.label));

                        let outputFeatures = trackFeatures.filter(function(f)
                        {
                           if(f.start !== query['start'] || f.ref !== query['ref'] || f.end !== query['end'])
                           {
                               return f;
                           }
                        });

                        localStorage.setItem(track.config.label, JSON.stringify(outputFeatures));
                    }
                }
            });

            callback();
        },
        saveStore() {
            return {
                urlTemplate: this.config.blob.url
            };
        }

    });
});
