define([

    'dojo/_base/declare',
    'dojo',
    'dojo/on',
    'dojo/mouse',
    'JBrowse/Util',
    'InteractivePeakAnnotator/View/Track/MultiXYPlot'
],
function (
    declare,
    dojo,
    on,
    mouse,
    Util,
    XYPlot
) {
    return declare([ XYPlot],
        {
            constructor: function(args)
            {
                this.inherited(arguments);
                const conf = this.config.storeConf;
                const CLASS = dojo.global.require(conf.modelClass);
                const newModel = Object.assign({}, args, conf);
                newModel.config = Object.assign({}, args.config, conf);
                this.modelStore = new CLASS(newModel);

                this.cacheKey = 0;

                let thisB = this;

                let updateCacheKey = function(){
                    let keys = Object.keys(thisB.browser.view.trackIndices);

                    if(keys.includes(thisB.key)) {
                        thisB.modelStore.cacheKey++
                        thisB.highlightStore.cacheKey++
                    }
                }
                dojo.subscribe('/jbrowse/v1/n/tracks/redraw', updateCacheKey)
            },
            _defaultConfig: function () {
                return Util.deepUpdate(dojo.clone(this.inherited(arguments)), {
                    addBackend: true,
                    PL: true,
                })
            },
            _postDraw: function (scale, leftBase, rightBase, block, canvas) {
                // Call WiggleHighlighter post draw
                this.inherited(arguments)

                let modelTypes = ['NONE', 'LOPART', 'FLOPART'];
                let typeToView;

                let heightVal = canvas.style.height + (block.domNode.offsetHeight - canvas.style.height)

                modelTypes.forEach(modelType => {
                    let menuCheck = dijit.byId(modelType)

                    if(menuCheck.checked)
                    {
                        typeToView = modelType
                    }
                })

                let vis = this.browser.view.visibleRegion();

                let visStart = vis['start'];
                let visEnd = vis['end'];

                this.modelStore.getFeatures({ ref: this.browser.refSeq.name,
                        start: leftBase,
                        end: rightBase,
                        width: canvas.width,
                        scale: scale,
                        visibleStart: visStart,
                        visibleEnd: visEnd,
                        modelType: typeToView},
                    feature => {
                        console.log(feature)
                        let s, e;

                        s = block.bpToX(
                            Math.max(
                                feature.get('start') - this.config.broaden,
                                block.startBase,
                            ),
                        );
                        e = block.bpToX(
                            Math.min(feature.get('end') + this.config.broaden, block.endBase),
                        );

                        const score = Math.round(feature.get('score'));
                        const height = (parseInt(heightVal, 10) - score) + "px";
                        let colors = {NONE: '#ff0000', LOPART: '#ff00a0', FLOPART: '#ff6f00'};
                        const indicator = dojo.create(
                            'div',
                            {
                                style: {
                                    left: `${s}px`,
                                    width: `${e - s}px`,
                                    height: `5px`,
                                    zIndex: 10000,
                                    top: height,
                                    position: 'absolute',
                                    backgroundColor: colors[feature.get('type').toUpperCase()] || '#0040ff'
                                },
                                class: 'Model',
                            },
                            block.domNode,
                            );
                    },
                    () => {},
                    error => {
                        console.error(error)
                    });
            },
        });
});
