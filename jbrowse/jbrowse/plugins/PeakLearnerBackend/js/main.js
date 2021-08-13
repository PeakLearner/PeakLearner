define([
        'dojo/_base/declare',
        'dojo/_base/lang',
        'dojo/Deferred',
        'dojo/dom',
        'dojo/dom-construct',
        'dojo/request',
        'dijit/MenuSeparator',
        'dijit/form/DropDownButton',
        'dijit/DropDownMenu',
        'dijit/form/Button',
        'dijit/registry',
        'dijit/MenuItem',
        'JBrowse/Util',
        'JBrowse/Plugin',
        './View/NewHub',
        'dijit/MenuItem',
        'dijit/Menu',
        'dijit/PopupMenuItem',
        'dijit/RadioMenuItem',
    ],
    function (
        declare,
        lang,
        Deferred,
        dom,
        domConstruct,
        dojoRequest,
        dijitMenuSeparator,
        dijitDropDownButton,
        dijitDropDownMenu,
        dijitButton,
        dijitRegistry,
        dijitMenuItem,
        Util,
        JBrowsePlugin,
        NewHub,
        MenuItem,
        Menu,
        PopupMenuItem, RadioMenuItem
    ) {
        return declare(JBrowsePlugin,
            {
                constructor: function (args) {
                    var thisB = this;
                    var myBrowser = this.browser;

                    console.log('PeakLearner plugin starting');
                    myBrowser.afterMilestone('initView', function () {

                        var datasetButton = new dijitMenuItem({
                            label: 'Upload New Dataset',
                            iconClass: 'dijitIconNewTask',
                            id: 'uploadData',
                            onClick: lang.hitch(thisB, 'newDataset')
                        });

                        myBrowser.addGlobalMenuItem('peaklearner', datasetButton);

                        var unlabeledButton = new dijitMenuItem({
                            label: 'Go to unlabeled region',
                            id: 'unlabeledRegion',
                            onClick: lang.hitch(thisB, 'goToUnlabeled')
                        });

                        myBrowser.addGlobalMenuItem('peaklearner', unlabeledButton);

                        var labeledButton = new dijitMenuItem({
                            label: 'Go to labeled region',
                            id: 'labeledRegion',
                            onClick: lang.hitch(thisB, 'goToLabeled')
                        });

                        myBrowser.addGlobalMenuItem('peaklearner', labeledButton);


                        let modelTypes = ['FLOPART', 'LOPART'];
                        let colors = {PEAK: '#ff0000', LOPART: '#ff00a0', FLOPART: '#ff6f00'};

                        let modelTypeMenu = new Menu({id: 'modelTypeMenu'});
                        modelTypes.forEach(type => {
                            modelTypeMenu.addChild(new RadioMenuItem({
                                label: type,
                                checked: (type === 'FLOPART'),
                                class: 'modelMenuItem',
                                id: type,
                                style: {
                                  background: colors[type]
                                },
                                onClick: (e) => {
                                    let selectedState = e.target.innerHTML;

                                    modelTypes.forEach(currentType => {
                                        if (currentType !== selectedState)
                                        {
                                            let currentMenuItem = dijit.byId(currentType)

                                            currentMenuItem.set('checked', false);
                                        }
                                    })
                                    myBrowser.view.redrawTracks()
                                }
                            }));
                        });


                        myBrowser.addGlobalMenuItem('peaklearner',
                            new PopupMenuItem({
                                label: 'Secondary Model Display Type',
                                popup: modelTypeMenu
                            }));


                        if (dijitRegistry.byId('dropdownmenu_peaklearner') === undefined) {
                            myBrowser.renderGlobalMenu('peaklearner', {text: 'PeakLearner'}, myBrowser.menuBar);
                        }

                    });

                    let addLabels = (data) => {
                        if (data.length > 0) {
                            let annotation = data[0];


                            let addCallback = function (data) {
                                //console.log(data);
                            }

                            let indices = this.browser.view.trackIndices

                            let keys = Object.keys(indices);

                            let tracks = [];

                            keys.forEach(key => {
                                if (this.browser.view.tracks[indices[key]].config['PL']) {
                                    tracks.push(key)
                                }
                            });

                            if (tracks.length > 0) {
                                this.addFeatures(annotation, tracks, addCallback);
                            }

                            this.browser.clearHighlight();
                            this.browser.view.behaviorManager.swapBehaviors('highlightingMouse', 'normalMouse');
                        }
                    }

                    dojo.subscribe('/jbrowse/v1/n/globalHighlightChanged', addLabels)

                    console.log('PeakLearner plugin added');
                },
                addFeatures: function (annotation, tracks, addCallback) {
                    let currentLabel = dijit.byId('current-label');

                    let indices = this.browser.view.trackIndices;

                    annotation['label'] = currentLabel.value;

                    annotation['tracks'] = tracks

                    //Get PL track so addFeatures can be used
                    let track = this.browser.view.tracks[indices[tracks[0]]]

                    track.highlightStore.addFeatures(annotation, addCallback)
                },
                goToUnlabeled: function () {
                    this.goToRegion("unlabeled");
                },
                goToLabeled: function () {
                    this.goToRegion("labeled");
                },
                goToRegion: function (region) {

                    let regionCallback = (data) => {
                        if (data) {
                            this.browser.navigateToLocation(data)
                        }
                    };

                    let url = this.browser.config.baseUrl + region;

                    let xhrArgs = {
                        url: url,
                        handleAs: "json",
                        load: regionCallback
                    };

                    var deferred = dojo.xhrGet(xhrArgs);
                },
                newDataset: function () {
                    var hub = new NewHub();
                    var browser = this.browser;
                    hub.show(browser, function (searchParams) {
                        if (searchParams) {
                            console.log(searchParams);
                        }
                    })
                }
            });
    });
