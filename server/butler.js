var EventEmitter = require('events').EventEmitter;
var util = require('util');

function Butler(config) {
  this.config = config || {};
  this.servants = {};
}

Butler.prototype = {
  hire: function(servant) {
    var name = servant.name;
    var config = this.config[name] || {};
    this.servants[name] = new servant(this, config);
  },

  call: function(method) {
    var args = Array.prototype.slice.call(arguments, 1);
    var split = method.split('.')
    if (split.length != 2 || !split[0] || !split[1] ||
        split[1].charAt(0) === '_') {
      throw new Error('malformed or invalid method name "' + method + '"');
    }
    var servant = this.servants[split[0]];
    return servant[split[1]].apply(servant, args);
  }
};

util.inherits(Butler, EventEmitter);

module.exports = {
  Butler: Butler
};
