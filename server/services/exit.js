var process = require('process');

var butler = require('../butler');

exports.start = function() {
  process.on('exit', function(code) {
    butler.emit('exit', code);
  });

  process.on('SIGINT', function() {
    process.exit(0);
  });

  process.on('uncaughtException', function(err) {
    process.exit(1);
  });
}
