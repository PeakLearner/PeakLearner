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

               if(data.length != 0)
               {
                  localStorage.clear()
                  localStorage.setItem("label", data[0].ref + " " + data[0].start + " " + data[0].end);
                  localStorage.setItem("UILable", "true");
               }
               else
               {
                  if(localStorage.getItem("tracks") === null)
                  {
                     
                  }
                  else
                  {
                     var labelInfo = localStorage.getItem("label").split(" ");
                     var tracks = localStorage.getItem("tracks").split(" ");
                     var jsonArray = Array();
                     for(var i = 0; i < tracks.length - 1; i++)
                     {
                        jsonArray.push({"chr": labelInfo[0],
                        "start": labelInfo[1],
                        "end": labelInfo[2],
                        "name": tracks[i],
                        "peakType": localStorage.getItem(tracks[i] + " peakType")});
                     }
                     
                     console.log(jsonArray)
                     localStorage.setItem("UILable", "false");
                     var xhr = new XMLHttpRequest();
                     xhr.open("POST", '/send' , true);
                     xhr.setRequestHeader('Content-Type', 'application/json');
                     xhr.send(jsonArray);
                  }
               }
            });
        }
    });
});
