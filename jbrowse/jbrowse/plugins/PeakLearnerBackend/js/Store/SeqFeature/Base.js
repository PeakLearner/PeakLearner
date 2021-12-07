define([
        'dojo/_base/declare',
        'dojo/_base/lang',
        'dojo/_base/array',
        'dojo/io-query',
        'dojo/request',
        'dojo/Deferred',
        'JBrowse/Util',
        'JBrowse/Model/SimpleFeature',
        'JBrowse/View/Track/_FeatureDetailMixin',
        'JBrowse/Store/LRUCache',
        'dojo/request/xhr'
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
        FeatureDetailMixin,
        LRUCache,
        xhr
    ) {
        return declare(FeatureDetailMixin, {
            constructor: function (args) {
                // make sure the baseUrl has a trailing slash
                this.baseUrl = args.baseUrl || this.config.baseUrl;
                if (this.baseUrl.charAt(this.baseUrl.length - 1) != '/')
                    this.baseUrl = this.baseUrl + '/';

                this.name = args.name || this.config.label;
                this.track = args.track || this.config.key
                this.query = "base"

                this.cacheKey = 0;
            },
            getFeatures: function (query, featCallback, finishCallback, errorCallback) {
                var thisB = this;
                var cache = this.featureCache = this.featureCache || new LRUCache({
                    name: thisB.handler,
                    fillCallback: dojo.hitch(this, '_readChunk'),
                    sizeFunction: function (features) {
                        return features.length;
                    },
                    maxSize: 100000
                });
                query.toString = function () {
                    return query.ref + ',' + query.start + ',' + query.end + ',' + thisB.cacheKey;
                };
                var visible = thisB.browser.view.visibleRegion()
                var chunkSize = visible['end'] - visible['start'];

                var s = visible['start'] - visible['start'] % chunkSize;
                var e = visible['end'] + (chunkSize - (visible['end'] % chunkSize));
                chunkSize = e - s;
                var chunks = [];

                var chunksProcessed = 0;
                var haveError = false;
                for (var start = s; start < e; start += chunkSize) {
                    // Originally was var chunk = query but js is pass by reference so setting chunk also set the query
                    var chunk = dojo.clone(query);
                    chunk['start'] = start
                    chunk['end'] = start + chunkSize
                    chunk.toString = function () {
                        return chunk.ref + ',' + chunk.start + ',' + chunk.end + ',' + this.cacheKey;
                    };
                    chunks.push(chunk);
                }


                array.forEach(chunks, function (c) {
                    cache.get(c, function (f, err) {
                        if (err && !haveError) {
                            errorCallback(err);
                        }
                        haveError = haveError || err;
                        if (haveError) {
                            return;
                        }
                        thisB._resultsToFeatures(f, function (feature) {
                            if (feature.get('start') > query.end) {
                                // past end of range, can stop iterating
                                return;
                            } else if (feature.get('end') >= query.start) {
                                // must be in range
                                featCallback(feature);
                            }
                        });

                        if (++chunksProcessed === chunks.length) {
                            finishCallback();
                        }
                    });
                });
            },
            _resultsToFeatures: function (results, featCallback) {
                if (results) {
                    results.forEach(data => {
                        featCallback(new SimpleFeature({data}))
                    })
                }
            },
            _readChunk: function (query, callback) {
                this.sendGet(query, callback)
            },
            addFeature: function (query, callback) {
                this.sendPut(query, this.getHubHandlerUrl(), callback);
            },
            addFeatures: function (query, callback) {
                this.sendPut(query, this.getHubHandlerUrl(), callback);
            },
            updateFeature: function (query, callback) {
                this.sendPost(query, this.getHandlerUrl(), callback);
            },
            updateAlignedFeatures(query, callback) {
                let visibleTracks = this.getVisibleTracks();
                if (visibleTracks.length > 0) {
                    query['tracks'] = visibleTracks
                    this.sendPost(query, this.getHubHandlerUrl(), callback);
                }
            },
            removeFeature: function (query, callback) {
                this.sendDelete(query, this.getHandlerUrl(), callback);
            },
            removeAlignedFeatures(query, callback) {
                let visibleTracks = this.getVisibleTracks();
                if (visibleTracks.length > 0) {
                    query['tracks'] = visibleTracks
                    this.sendDelete(query, this.getHubHandlerUrl(), callback)
                }
            },
            getVisibleTracks: function( ) {
                let currentStore = this.config.storeClass;

                let tracksToCheck = [];

                this.browser.view.tracks.forEach(track => {
                    if (track.config.storeConf) {
                        if (track.config.storeConf.storeClass === currentStore) {
                            tracksToCheck.push(track.config.label)
                        }
                    }
                })

                return tracksToCheck;
            },
            sendGet: function (query, callback, url) {
                query['name'] = this.name;

                if (!url)
                {
                    url = this.getHandlerUrl()
                }

                let xhrArgs = {
                    handleAs: 'json',
                    method: 'get',
                    query: query
                };
                xhr(url, xhrArgs).then(
                    function (data) {
                        callback(data)
                    },
                    function (err) {
                        console.log(err)
                    }
                );
            },
            sendPut: function (query, queryUrl, callback) {
                query['name'] = this.name;

                let xhrArgs = {
                    handleAs: 'json',
                    method: 'PUT',
                    data: JSON.stringify(query),
                    sync: true,
                    headers: {'Content-Type': 'application/json'}
                };
                xhr(queryUrl, xhrArgs).then(
                    function (data) {
                        callback(data)
                    },
                    function (err) {
                        console.log(err)
                    }
                );
            },
            sendPost: function (query, queryUrl, callback) {
                query['name'] = this.name;

                let xhrArgs = {
                    handleAs: 'json',
                    method: 'post',
                    data: JSON.stringify(query),
                    headers: {'Content-Type': 'application/json'}
                };
                xhr(queryUrl, xhrArgs).then(
                    function (data) {
                        callback(data)
                    },
                    function (err) {
                        console.log(err)
                    }
                );
            },
            sendDelete: function (query, queryUrl, callback) {
                query['name'] = this.name;

                let xhrArgs = {
                    handleAs: 'json',
                    method: 'delete',
                    data: JSON.stringify(query),
                    headers: {'Content-Type': 'application/json'}
                };
                xhr(queryUrl, xhrArgs).then(
                    function (data) {
                        callback(data)
                    },
                    function (err) {
                        console.log(err)
                    }
                );
            },
            getHandlerUrl: function () {
                return this.track + '/' + this.handler
            },
            getHubHandlerUrl: function() {
                return this.handler
            },
            // Acquired from jbrowse/Store/SeqFeature/REST.js
            _errorHandler: function (handler) {
                handler = handler || function (e) {
                    console.error(e, e.stack);
                    throw e;
                };
                return dojo.hitch(this, function (error) {
                    var httpStatus = ((error || {}).response || {}).status;
                    if (httpStatus >= 400) {
                        handler("HTTP " + httpStatus + " fetching " + error.response.url + " : " + error.response.text);
                    } else {
                        handler(error);
                    }
                });
            },
            saveStore() {
                return {
                    urlTemplate: this.config.blob.url
                };
            }

        });
    });
