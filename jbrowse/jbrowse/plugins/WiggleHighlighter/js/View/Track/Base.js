define([
    'dojo/_base/declare',
    'dojo/on',
    'dojo/mouse',
    'dojo/dom-construct',
    'dojo/_base/event',
    'dijit/Dialog',
    'JBrowse/Util',
    'JBrowse/Store/SeqFeature/BigBed',
    'JBrowse/View/Track/_FeatureDetailMixin',
], function (declare, on, mouse, dom, domEvent, Dialog, Util, BigBed, FeatureDetailMixin) {
    return declare(FeatureDetailMixin, {
        constructor: function (args) {
            if (this.config.bigbed) {
                this.highlightStore = new BigBed(
                    Object.assign({}, this.config.bigbed, args),
                )
            } else {
                const conf = this.config.storeConf
                const CLASS = dojo.global.require(conf.storeClass)
                const newConf = Object.assign({}, args, conf)
                newConf.config = Object.assign({}, args.config, conf)
                this.highlightStore = new CLASS(newConf)
            }
        },
        _defaultConfig: function () {
            return Util.deepUpdate(dojo.clone(this.inherited(arguments)), {
                highlightColor: '#f0f2',
                indicatorColor: '#f0f',
                indicatorHeight: 3,
                broaden: 0,
                showLabels: false,
                dojoMenu: false,
                style: {
                    label: (feature, track) => feature.get('name') || feature.get('id'),
                },
                onHighlightClick: feature =>
                    new Dialog({
                        content: this.defaultFeatureDetail(this, feature, null, null, null),
                    }).show(),
                onHighlightRightClick: () => {
                },
                addMenu: (track, feature, highlight) => {
                },
            })
        },
        _postDraw: function (scale, leftBase, rightBase, block, canvas) {
            this.highlightStore.getFeatures(
                {ref: this.browser.refSeq.name, start: leftBase, end: rightBase},
                feature => {
                    const s = block.bpToX(
                        Math.max(
                            feature.get('start') - this.config.broaden,
                            block.startBase,
                        ),
                    )
                    const e = block.bpToX(
                        Math.min(feature.get('end') + this.config.broaden, block.endBase),
                    )

                    const highlight = dom.create('div', {
                        style: {
                                left: `${s}px`,
                                width: `${e - s}px`,
                                height: canvas.style.height
                        },
                        class: 'Label'
                    }, block.domNode)

                    const ret = dom.create(
                        'div',
                        {
                            style: {
                                left: `${s}px`,
                                width: `${e - s}px`,
                                height: canvas.style.height,
                                top: 0,
                                zIndex: 10000,
                                position: 'absolute',
                                backgroundColor:
                                    typeof this.config.highlightColor === 'function'
                                        ? this.config.highlightColor(feature, this)
                                        : this.config.highlightColor,
                            },
                            class: 'LabelBody'
                        },
                        highlight,
                    )
                    const indicator = dom.create(
                        'div',
                        {
                            style: {
                                left: `${s}px`,
                                width: `${e - s}px`,
                                height: `${this.config.indicatorHeight}px`,
                                zIndex: 10000,
                                top: canvas.style.height,
                                position: 'absolute',
                                backgroundColor:
                                    typeof this.config.indicatorColor === 'function'
                                        ? this.config.indicatorColor(feature, this)
                                        : this.config.indicatorColor,
                            },
                            class: 'LabelIndicator'
                        },
                        highlight,
                    )
                    // draw label
                    const label =
                        this.config.showLabels && this.config.style.label(feature, this)
                    let domLabel
                    if (label) {
                        const textLeft = block.bpToX(
                            feature.get('start') - this.config.broaden,
                        )
                        if (leftBase <= feature.get('start')) {
                            domLabel = dom.create(
                                'div',
                                {
                                    style: {
                                        left: `${textLeft}px`,
                                        top: 0,
                                        zIndex: 100000,
                                        position: 'absolute',
                                    },
                                    innerHTML: this.config.style.label(feature, this),
                                    class: 'LabelText',
                                },
                                highlight,
                            )
                        }

                    }

                    if (this.config.dojoMenu) {
                        this.config.addMenu(this, feature, highlight)
                    }

                    const effectiveCallback = event => {
                        if (mouse.isRight(event)) {
                            this.getConf('onHighlightRightClick', [feature, this, event])
                        } else {
                            this.getConf('onHighlightClick', [feature, this, event])
                        }
                        event.stopPropagation()
                    }

                    const cancelCallback = event => {
                        event.preventDefault();
                        event = domEvent.fix(event)
                        domEvent.stop(event)
                    }

                    let toListen = [indicator, ret];

                    if (domLabel) {
                        toListen.push(domLabel);
                    }

                    toListen.forEach(e => {
                        on(e, 'contextMenu', cancelCallback);
                        on(e, 'dblclick', cancelCallback);
                        on(e, 'mousedown', effectiveCallback);
                    })

                },
                () => {
                },
                error => {
                    console.error(error)
                },
            )
        },
    })
})
