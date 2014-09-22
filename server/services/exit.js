var butler = require('../butler');

module.exports = function() {
  process.on('exit', function(code) {
    butler.emit('exit', code);
  });

  process.on('SIGINT', function() {
    process.emit('log.info', 'SIGINT');
    process.exit(0);
  });

  process.on('SIGTERM', function() {
    process.emit('log.info', 'SIGTERM');
    process.exit(0);
  });

  process.on('uncaughtException', function(err) {
    console.log(err.stack);
    process.emit('log.fatal', err);
    process.exit(1);
  });
};
