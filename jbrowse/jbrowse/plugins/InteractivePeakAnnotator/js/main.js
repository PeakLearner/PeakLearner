define([
    'dojo/_base/declare',
    'dojo/dom-construct',
    'dijit/form/Select',
    'JBrowse/Plugin',
],
function (
    declare,
    dom,
    Select,
    JBrowsePlugin,
) {
    return declare(JBrowsePlugin, {
        // eslint-disable-next-line no-unused-vars
        constructor: function (args) {
            var thisB = this;
            console.log('InteractivePeakAnnotator plugin starting test');
            let browser = this.browser;
            let labelOptions = [{label: "peakStart", value: "peakStart", selected: true},
                                {label: "peakEnd", value: "peakEnd"},
                                {label: "noPeak", value: "noPeak"}]
            browser.afterMilestone('initView', function () {
                let navbox = dojo.byId('navbox');
                thisB.browser.labelDropdown = new Select({
                    name: "Select",
                    id: "current-label",
                    options: labelOptions
                }, dojo.create('div', {id: 'current-Label'}, navbox))
            });
        }
    });
});
