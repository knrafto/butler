var process = require('process');

var butler = require('../butler');

exports.start = function() {
  process.on('exit', function(code) {
    butler.emit('exit', code);
  });

  process.on('SIGINT', function() {
    process.exit();
  });

  process.on('uncaughtException', function(err) {
    console.log(err.stack);
    process.exit(1);
  });
}
