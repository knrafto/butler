var butler = require('../butler');

module.exports = function(config) {
  config = config || {};

  butler.register('key', function() {
    var name = this.method.replace(/^key\./, '');
    var value = config[name];
    butler.emit('log.debug', 'key', name, value);
    return value;
  });
};
