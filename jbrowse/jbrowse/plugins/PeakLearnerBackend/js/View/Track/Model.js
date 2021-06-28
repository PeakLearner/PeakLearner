define([
    'dojo/_base/declare',
    'dojo',
    'dojo/on',
    'dojo/mouse',
    'JBrowse/Util',
    'dijit/Menu',
    'dijit/PopupMenuItem',
    'dijit/MenuItem',
    'dijit/Dialog',
    'InteractivePeakAnnotator/View/Track/MultiXYPlot',
    ],
function (
    declare,
    dojo,
    on,
    mouse,
    Util,
    Menu,
    PopupMenuItem,
    MenuItem,
    Dialog,
    XYPlot,
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

                this.addBlockMenu(block, this.browser.refSeq.name, visStart, visEnd);

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
            addBlockMenu: function(block, ref, visStart, visEnd)  {
                let menu = new Menu();

                let jobCallback = (jobs) =>
                {
                    let container = dojo.create('div', { className: 'detail feature-detail', innerHTML: '' } );

                    this._renderCoreDetails(container, ref, visStart, visEnd)

                    let jobsSection = dojo.create('div', { className: 'Jobs section'}, container)
                    jobsSection.innerHTML += '<h2 class="sectiontitle">Jobs</h2>'

                    jobs.forEach(job => {
                        let jobDiv = dojo.create('div', {className: 'job-' + job.id}, jobsSection)
                        jobDiv.innerHTML += '<h4> Job ID: ' + job.id + '</h4>';
                        jobDiv.innerHTML += '<h6> Status: ' + job.status + '</h6>';
                        jobDiv.innerHTML += '<h6> Type: ' + job.jobType + '</h6>';
                        jobDiv.innerHTML += '<h6> Priority: ' + job.priority + '</h6>';
                        jobDiv.innerHTML += '<h6> Last Modified: ' + job.lastModified + '</h6>';


                        let tasksDiv = dojo.create('div', {className: 'job-' + job.id + '-tasks',
                        innerHTML: '<h3>Tasks</h3><hr>'}, jobDiv)

                        let tasks = job.tasks;

                        Object.keys(job.tasks).forEach(taskId => {
                            let task = tasks[taskId];
                            let taskDiv = dojo.create('div', {className: 'job-' + job.id + '-task-' + taskId}, tasksDiv);
                            taskDiv.innerHTML += '<h4>Task ID: ' + task.taskId + '</h4><hr>';
                            taskDiv.innerHTML += '<h5>Type: ' + task.type + '</h5>';
                            taskDiv.innerHTML += '<h5>Status: ' + task.status + '</h5>';
                            if (task.type === 'model') {
                                taskDiv.innerHTML += '<h5>Penalty: ' + task.penalty + '</h5>';
                            }


                        })

                    })

                    new Dialog({
                        title: 'Job Stats',
                        content: container
                    }).show()
                }

                menu.addChild(new MenuItem({
                    label: 'Job stats',
                    onClick: event => {
                        let query = {ref: ref, start: visStart, end: visEnd}
                        let url = this.modelStore.track + '/jobs/'
                        console.log(url)
                        this.modelStore.sendGet(query, jobCallback, url)
                    }
                }))

                let modelCallback = (modelSums) => {
                    let container = dojo.create('div', {className: 'detail feature-detail', innerHTML: ''});

                    this._renderCoreDetails(container, ref, visStart, visEnd)

                    let modelSumsSection = dojo.create('div', {className: 'Model Summaries section'}, container)
                    modelSumsSection.innerHTML += '<h2 class="sectiontitle">Model Summaries</h2>'


                    new Dialog({
                        title: 'Model Summaries',
                        content: container
                    }).show()
                }

                menu.addChild(new MenuItem({
                    label: 'Model stats',
                    onClick: (event, test) => {
                        let query = {ref: ref, start: visStart, end: visEnd}
                        let url = this.modelStore.track + '/modelSums/'
                        console.log(url)
                        this.modelStore.sendGet(query, modelCallback, url)
                    }
                }))


                menu.bindDomNode(block.domNode)
                menu.startup();
            },
            _renderCoreDetails(container, ref, visStart, visEnd)
            {
                var coreDetails = dojo.create('div', { className: 'core' }, container );
                let conf = this.browser.config;
                coreDetails.innerHTML += '<h2 class="sectiontitle">Hub: ' + conf.hub + '</h2>';
                coreDetails.innerHTML += '<h3>Owner: ' + conf.owner + '</h3>';
                coreDetails.innerHTML += '<h3>Track: ' + this.modelStore.track + '</h3>'
                coreDetails.innerHTML += '<h3>Current Ref: ' + ref + '</h3>'
                coreDetails.innerHTML += '<h3>Visible Start: ' + visStart + '</h3>'
                coreDetails.innerHTML += '<h3>Visible End: ' + visEnd + '</h3>'



            },
        });
});
