var process = require('process');
var _ = require('underscore');

var butler = module.exports = _.clone(require('./bus'));

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
