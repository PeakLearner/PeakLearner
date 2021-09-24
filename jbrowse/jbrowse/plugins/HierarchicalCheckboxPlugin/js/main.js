/*
CategoryTrackListCheckboxes JBrowse plugin
*/
/*
    Created on : Feb 17, 2016
    Author     : Brigitte Hofmeister
*/

define("HierarchicalCheckboxPlugin/main", [
        'dojo/_base/declare',
        'JBrowse/Plugin',
        'dojo/_base/array',
        'dojo/_base/lang',
        'dojo/query',
        'dojo/dom',
        'dojo/dom-construct',
        'dojo/on',
        'dijit/TitlePane',
        'dijit/form/CheckBox',
        'JBrowse/Util'
    ],
    function (
        declare,
        JBrowsePlugin,
        array,
        lang,
        query,
        dom,
        domConstruct,
        on,
        TitlePane,
        CheckBox,
        Util
    ) {
        return declare(JBrowsePlugin, {
            constructor: function (args) {
                console.log("HierarchicalCheckboxPlugin starting");
                this.config.version = '1.0.2';

                var thisB = this;
                var browser = this.browser;
                //console.log("plugin: TrackScore");

                browser.afterMilestone('loadConfig', function () {
                    if (typeof browser.config.classInterceptList === 'undefined') {
                        browser.config.classInterceptList = {};
                    }
                    // override WiggleBase
                    require(["dojo/_base/lang", "JBrowse/View/TrackList/Hierarchical"], function (lang, Hierarchical) {
                        lang.extend(Hierarchical, {
                            addTracks: thisB.addTracks
                        });
                    });
                });
            },

            addTracks: function (tracks, inStartup) {
                this.pane = this;
                var thisB = this;

                array.forEach(tracks, function (track) {
                    var trackConf = track.conf || track;

                    var categoryFacet = this.get('categoryFacet');
                    var categoryNames = (
                        trackConf.metadata && trackConf.metadata[categoryFacet] ||
                        trackConf[categoryFacet] ||
                        track[categoryFacet] ||
                        'Uncategorized'
                    ).split(/\s*\/\s*/);

                    var category = _findCategory(this, categoryNames, []);

                    function _findCategory(obj, names, path) {
                        //console.log(thisB);
                        var categoryName = names.shift();
                        path = path.concat(categoryName);
                        var categoryPath = path.join('/');
                        var categoryGoodName = categoryPath.split(/\s+|\//g).join('-');
                        //console.log(obj);
                        //console.log(obj.categories[categoryName] );
                        var cat = obj.categories[categoryName] || (obj.categories[categoryName] = function () {
                            var isCollapsed = lang.getObject('collapsed.' + categoryPath, false, thisB.state);
                            var checkBoxId = categoryGoodName + '_checkBox';

                            var labelDom = domConstruct.create('label', {
                                'title': 'select/deselect all tracks from this category',
                                'className': 'category-select'
                            });
                            domConstruct.create('span', {
                                innerHTML: 'select all from category'
                            }, labelDom);

                            var checkDom = domConstruct.create('input', {
                                'type': 'checkbox',
                                'class': 'hierachcheck',
                                'id': checkBoxId,
                                'value': categoryPath
                            }, labelDom);

                            var c = new TitlePane({
                                title: '<span class="categoryName">' + categoryName + '</span>' + ' <span class="trackCount">0</span>',
                                open: !isCollapsed,
                                content: labelDom
                            });
                            // save our open/collapsed state in local storage
                            c.watch('open', function (attr, oldval, newval) {
                                lang.setObject('collapsed.' + categoryPath, !newval, thisB.state);
                                thisB._saveState();
                            });
                            var listener;
                            obj.pane.own(listener = on(checkDom, 'change', function () {
                                var categoryStr = this.value,
                                    categoryList = thisB.categories,
                                    isChecked = this.checked;

                                _updateCategory(categoryStr, categoryList, isChecked);

                                function _updateCategory(categoryStr, categoryObj, isChecked) {
                                    var catList = categoryStr.split('/');
                                    for (var j = 0; j < catList.length; j++)
                                        catList[j] = catList[j].replace(/^[ ]+|[ ]+$/g, ''); //trim leading/trailing spaces
                                    var categoryList = [];
                                    // loop through categories
                                    var catSize = 0,
                                        key;
                                    for (key in categoryObj) {
                                        if (categoryObj.hasOwnProperty(key)) {
                                            catSize++;
                                            categoryList.push(key);
                                        }
                                    }
                                    for (var i = 0; i < catSize; i++) {
                                        // category name
                                        var testCat = categoryObj[categoryList[i]];
                                        if (testCat) {
                                            if (testCat.hasOwnProperty('box')) {
                                                var tCatList = testCat.box.value.split('/');
                                                for (var j = 0; j < tCatList.length; j++)
                                                    tCatList[j] = tCatList[j].replace(/^[ ]+|[ ]+$/g, ''); //trim leading/trailing spaces

                                                var catMatch = true;
                                                // determine if category matches
                                                if (catList.length <= tCatList.length) {
                                                    for (var j = 0; j < catList.length; j++)
                                                        if (catList[j] != tCatList[j]) catMatch = false;
                                                }
                                                // is match
                                                if (catMatch) {
                                                    // update check box
                                                    // testCat.box.checked = isChecked;
                                                    //count subcategories
                                                    catSize = 0;
                                                    for (key in testCat.categories) {
                                                        if (testCat.categories.hasOwnProperty(key)) catSize++;
                                                    }
                                                    if (catSize > 0)
                                                        _updateCategory(categoryStr, testCat.categories, isChecked);
                                                }
                                            }
                                        }
                                    }
                                }

                                _updateCategoryTracks(categoryList, this.value, this.checked);

                                function _updateCategoryTracks(categoryObj, categoryStr, isChecked) {
                                    //console.log('categorytracks ' + categoryStr);
                                    var tracks = thisB.browser.config.tracks;
                                    var catlist = categoryStr.split("/");

                                    for (var j = 0; j < catlist.length; j++) {
                                        catlist[j] = catlist[j].replace(/^[ ]+|[ ]+$/g, '');
                                    } //trim leading/trailing spaces
                                    var tracksToShow = [];
                                    for (var i = 0; i < tracks.length; i++) {
                                        //console.log("track "+i+" ("+tracks[i].category+") "+tracks[i].label);

                                        var t_catlist = [];
                                        // handle track.metadata.category
                                        if (typeof (tracks[i].metadata) !== 'undefined' && typeof (tracks[i].metadata.category) !== 'undefined')
                                            t_catlist = tracks[i].metadata.category.split("/");

                                        // handle track.category
                                        if (typeof (tracks[i].category) !== 'undefined')
                                            t_catlist = tracks[i].category.split("/");


                                        if (catlist.length <= t_catlist.length) {
                                            for (var j = 0; j < t_catlist.length; j++)
                                                t_catlist[j] = t_catlist[j].replace(/^[ ]+|[ ]+$/g, ''); //trim leading/trailing spaces

                                            var match = true;
                                            for (var j = 0; j < catlist.length; j++) {
                                                if (catlist[j] !== t_catlist[j]) match = false;
                                            }

                                            let cats = categoryObj[t_catlist[0]].categories

                                            let cat = cats[t_catlist[1]]

                                            // if there's a match, show the track
                                            if (match && cat.pane.open) {
                                                cat.box.checked = isChecked;
                                                //console.log("match!")
                                                tracksToShow.push(tracks[i]);
                                            }
                                        }
                                    }

                                    if (tracksToShow.length > 0)
                                        thisB.browser.publish('/jbrowse/v1/v/tracks/' + (isChecked ? 'show' : 'hide'), tracksToShow);
                                }
                            }));
                            obj.pane.addChild(c, inStartup ? undefined : 1);
                            return {
                                parent: obj,
                                pane: c,
                                categories: {},
                                tracks: {},
                                box: checkDom
                            };
                        }.call(thisB));

                        return names.length ? _findCategory(cat, names, path) : cat;
                    };

                    category.pane.domNode.style.display = 'block';

                    // note: sometimes trackConf.description is defined as numeric, so in this case, ignore it
                    var labelNode = domConstruct.create(
                        'label', {
                            className: 'tracklist-label shown',
                            title: Util.escapeHTML(trackConf.shortDescription || track.shortDescription || (trackConf.description === 1 ? undefined : trackConf.description) || track.description || trackConf.Description || track.Description || trackConf.metadata && (trackConf.metadata.shortDescription || trackConf.metadata.description || trackConf.metadata.Description) || track.key || trackConf.key || trackConf.label)
                        }, category.pane.containerNode);

                    var checkbox = domConstruct.create('input', {
                        type: 'checkbox',
                        className: 'check'
                    }, labelNode);
                    var trackLabel = trackConf.label;
                    var checkListener;
                    this.own(checkListener = on(checkbox, 'click', function () {

                        thisB.browser.publish('/jbrowse/v1/v/tracks/' + (this.checked ? 'show' : 'hide'), [trackConf]);
                        // we need to add information to see how many tracks of the category are checked
                        //console.log(trackConf.category);
                        // get the category object
                        var category;
                        if (trackConf.hasOwnProperty('category')) {
                            category = trackConf.category
                        } else if (trackConf.hasOwnProperty('metadata') && trackConf.metadata.hasOwnProperty('category')) {
                            category = trackConf.metadata.category;
                        } else {
                            category = '';
                        }
                        var catList = category.split("/");
                        for (var j = 0; j < catList.length; j++)
                            catList[j] = catList[j].replace(/^[ ]+|[ ]+$/g, ''); //trim leading/trailing spaces
                        var cat = thisB;
                        // loop through categories/subcategories
                        _countCheckedTracks(cat, catList);

                        function _countCheckedTracks(cat, catList) {
                            if (catList.length == 0)
                                return [0, 0];
                            var newCat = cat.categories[catList[0]];
                            var keepCatList = lang.clone(catList.splice(1));
                            var countAr = _countCheckedTracks(newCat, catList.splice(1));
                            var otherCats = Object.keys(newCat.categories);

                            if (otherCats.length > 0) {
                                for (var i = 0; i < otherCats.length; i++) {
                                    if (otherCats[i] !== keepCatList[0]) {
                                        var tmp = _countCheckedTracks(newCat, [otherCats[i]]);
                                        countAr[0] += tmp[0];
                                        countAr[1] += tmp[1];
                                    }
                                }
                            }
                            // update counts for tracks in this specific category
                            var key;
                            for (key in newCat.tracks) {
                                if (newCat.tracks.hasOwnProperty(key)) {
                                    countAr[0]++;
                                    if (newCat.tracks[key].checkbox.checked) countAr[1]++;
                                }
                            }
                            // all checked
                            if (countAr[0] == countAr[1]) {
                                newCat.box.checked = true;
                                newCat.box.indeterminate = false;
                            } // none checked
                            else if (countAr[1] == 0) {
                                newCat.box.checked = false;
                                newCat.box.indeterminate = false;
                            } // some checked
                            else {
                                newCat.box.checked = false;
                                newCat.box.indeterminate = true;
                            }
                            return countAr;
                        }
                    }));
                    domConstruct.create('span', {
                        className: 'key',
                        innerHTML: trackConf.key || trackConf.label
                    }, labelNode);

                    category.tracks[trackLabel] = {
                        checkbox: checkbox,
                        checkListener: checkListener,
                        labelNode: labelNode
                    };

                    this._updateTitles(category);
                }, this);
            },

            _updateTitle: function (category) {
                var thisB = this;
                //console.log(category);
                category.pane.set('title', category.pane.get('title')
                    .replace(/>\s*\d+\s*</, '>' + query('label.shown', category.pane.containerNode).length + '<')
                );
                //console.log(category.box);
                //var checkboxDom = dom.byId(category.cName+'_checkBox');
                /*
                this.own(listener=on( checkboxDom, 'change', function(e) {
                    //e.stopPropagation();
                    if(this.checked)
                        thisB.setTracksActive(category.tracks);
                    else
                        thisB.setTracksInactive(category.tracks);
                    this.indeterminate = false;
                    }));
                console.log('end update title');*/
            },

            updateCategory: function (categoryStr, categoryList, isChecked) {
                // visible tracks
                //var visibleTracks = this.browser.view.visibleTracks;
                var catList = categoryStr.split('/');
                // loop through categories
                for (var i = 0; i < categoryList.length; i++) {
                    // category name
                    var tCatList = categoryList[i].box.value.split('/');
                    var catMatch = true;
                    // determine if category matches
                    if (catList.length <= tCatList.length) {
                        for (var j = 0; j < catList.length; j++)
                            if (catList[j] != tCatList[j]) catMatch = false;
                    }
                    // is match
                    // update check box
                    categoryList[i].box.checked = isChecked;
                    // recurse if necessary
                    if (categoryList[i].categories.length > 0)
                        this._updateCategory(categoryStr, categoryList[i].categories, isChecked);
                }
            },

            updateCategoryTracks: function (categoryStr, isChecked) {
                var thisB = this;
                var tracks = thisB.browser.config.tracks;
                var catlist = this.value.split("/");
                var tracksToShow = [];
                for (var i = 0; i < tracks.length; i++) {
                    //console.log("track "+i+" ("+tracks[i].category+") "+tracks[i].label);

                    var t_catlist = [];
                    // handle track.metadata.category
                    if (typeof (tracks[i].metadata) !== 'undefined' && typeof (tracks[i].metadata.category) !== 'undefined')
                        t_catlist = tracks[i].metadata.category.split("/");

                    // handle track.category
                    if (typeof (tracks[i].category) !== 'undefined')
                        t_catlist = tracks[i].category.split("/");

                    if (catlist.length <= t_catlist.length) {

                        for (var j = 0; j < t_catlist.length; j++)
                            t_catlist[j] = t_catlist[j].replace(/^[ ]+|[ ]+$/g, ''); //trim leading/trailing spaces

                        var match = true;
                        for (var j = 0; j < catCount; j++) {
                            if (catlist[j] != t_catlist[j]) match = false;
                        }
                        // if there's a match, show the track
                        if (match == true) {
                            //console.log("match!")
                            tracksToShow.push(tracks[i].label);
                        }
                    }
                }
                thisB.browser.publish('/jbrowse/v1/v/tracks/' + (isChecked ? 'show' : 'hide'), tracksToShow);
            }

        })
    });
