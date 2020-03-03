define([
    'dojo/_base/declare',
    'dojo/on',
    'dijit/Dialog',
    'JBrowse/Util',
    'JBrowse/Store/SeqFeature/BigBed',
    'JBrowse/View/Track/_FeatureDetailMixin'
],
function (
    declare,
    on,
    Dialog,
    Util,
    BigBed,
    FeatureDetailMixin
) {
    return declare(FeatureDetailMixin, {
        constructor: function (args) {
            if (this.config.bigbed) {
                this.highlightStore = new BigBed(Object.assign({}, this.config.bigbed, args));
            } else {
                const conf = this.config.storeConf;
                const CLASS = dojo.global.require(conf.storeClass);
                const newConf = Object.assign({}, args, conf);
                newConf.config = Object.assign({}, args.config, conf);
                this.highlightStore = new CLASS(newConf);
            }
        },
        _defaultConfig: function () {
            return Util.deepUpdate(
                dojo.clone(this.inherited(arguments)),
                {
                    highlightColor: '#f0f2',
                    indicatorColor: '#f0f',
                    indicatorHeight: 3,
                    broaden: 0
                }
            );
        },

        _postDraw: function (scale, leftBase, rightBase, block, canvas) {
            this.highlightStore.getFeatures({ref: this.browser.refSeq.name, start: leftBase, end: rightBase},
                feature => {
                    const s = block.bpToX(Math.max(feature.get('start') - this.config.broaden, block.startBase));
                    const e = block.bpToX(Math.min(feature.get('end') + this.config.broaden, block.endBase));
                    const ret = dojo.create('div', {
                        style: {
                            left: `${s}px`,
                            width: `${e - s}px`,
                            height: canvas.style.height,
                            top: 0,
                            zIndex: 10000,
                            position: 'absolute',
                            backgroundColor: this.getConf('highlightColor', [feature, this])
                        }
                    }, block.domNode);
                    const indicator = dojo.create('div', {
                        style: {
                            left: `${s}px`,
                            width: `${e - s}px`,
                            height: `${this.config.indicatorHeight}px`,
                            zIndex: 10000,
                            top: canvas.style.height,
                            position: 'absolute',
                            backgroundColor: this.getConf('indicatorColor', [feature, this])
                        }
                    }, block.domNode);

                    const callback = this.config.onHighlightClick ?
                        () => this.config.onHighlightClick(feature, this) :
                        () => new Dialog({ content: this.defaultFeatureDetail(this, feature, null, null, null) }).show();


                    on(indicator, 'click', callback)
                    on(ret, 'click', callback)

                },
                () => { },
                error => { console.error(error); }
            );
        }

    });
});
