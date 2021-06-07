try {
  define([
    'dojo/_base/declare',
    'JBrowse/Store/SeqFeature',
    './Base',
  ], function (declare, SeqFeature, Base) {
        return declare([ SeqFeature, Base ], {
            constructor: function(args)
            {
                this.inherited(arguments);
                this.handler = 'models'
            },
        })
  })
} catch (e) {}
