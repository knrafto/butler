var butler = require('../butler');

/**
 * @module exit A service that fires an 'exit' event when the server exists,
 * and logs exit conditions.
 */
module.exports = function() {
  process.on('exit', function(code) {
    butler.emit('exit', code);
  });

  process.on('SIGINT', function() {
    butler.emit('log.info', 'SIGINT');
    process.exit(0);
  });

  process.on('SIGTERM', function() {
    butler.emit('log.info', 'SIGTERM');
    process.exit(0);
  });

  process.on('uncaughtException', function(err) {
    console.log(err.stack);
    butler.emit('log.fatal', err);
    process.exit(1);
  });
};
