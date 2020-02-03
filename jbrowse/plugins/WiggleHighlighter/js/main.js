define([
    'dojo/_base/declare',
    'dojo/_base/lang',
    'dojo/Deferred',
    'JBrowse/Plugin'
],
function (
    declare,
    lang,
    Deferred,
    JBrowsePlugin
) {
    return declare(JBrowsePlugin, {
        constructor: function (/* args */) {
            console.log('WiggleHighlighter plugin starting');
            
            dojo.subscribe("/jbrowse/v1/n/globalHighlightChanged", function(data){
               console.log("Event inside: /jbrowse/v1/n/globalHighlightChanged",data);
            });
        }
    });
});
