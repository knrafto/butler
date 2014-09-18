var butler = require('../butler');

exports.start = function(config) {
  config = config || {};

  butler.register('key', function() {
    var name = this.method.replace(/^key\./, '');
    return config[name];
  });
}
