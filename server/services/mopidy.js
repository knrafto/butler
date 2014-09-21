var Mopidy = require('mopidy');
var _ = require('underscore');

var butler = require('../butler');

exports.start = function(config) {
  config = config || {};

  var mopidy = new Mopidy({
    webSocketUrl: config.url,
    callingConvention: 'by-position-or-by-name'
  });

  butler.register('mopidy', function(params) {
    var obj = mopidy;
    _.each(this.method.split('.').slice(1), function(part) {
      obj = obj[part];
    });
    return obj(params || {});
  });

  mopidy.on(function(name) {
    if (!name.match(/^event:/)) return;
    name = name.replace(/^event:/, 'mopidy.');
    var args = _.toArray(arguments).slice(1);
    butler.emit.apply(butler, [name].concat(args));
  });
};
