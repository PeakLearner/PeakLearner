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
            var highlightJSON = {}
            
            console.log('WiggleHighlighter plugin starting');
            
            dojo.subscribe("/jbrowse/v1/n/globalHighlightChanged", function(data){
               console.log("Event inside: /jbrowse/v1/n/globalHighlightChanged",data);
               if(data.length != 0)
               {
                  document.cookie = "name="+data[0].ref;
                  document.cookie = "start="+data[0].start
                  document.cookie = "end="+data[0].end;
                  console.log("test");
               }
            });

        }
    });
});
