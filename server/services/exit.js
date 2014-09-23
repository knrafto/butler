var butler = require('../butler');

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
