var fs = require('fs');
var util = require('util');
var _ = require('underscore');

var butler = require('../butler');

var loggers = [];
var levels = 'trace debug info warn error fatal'.split(' ');

function index(level) {
  return levels.indexOf(level);
}

function log(level, args) {
  try {
    args = _.map(args, function(obj) {
      return _.isString(obj) ? obj : util.inspect(obj);
    });
    var message = util.format(
      '%s %s: %s\n', Date(), level.toUpperCase(), args.join(' ')
    );
    _.each(loggers, function(logger) {
      if (index(level) < index(logger.level)) return;
      logger.stream.write(message);
    });
  } catch (err) {
    console.log('LOG ERROR:', err);
  }
}

module.exports = function(config) {
  config = config || {};

  if (config.console) {
    loggers.push({
      level: config.console.level,
      stream: process.stdout
    });
  }
  if (config.file) {
    loggers.push({
      level: config.file.level,
      stream: fs.createWriteStream(config.file.filename, { flags: 'a' })
    });
  }

  butler.on('log', function() {
    var level = this.event.replace(/^log\./, '');
    log(level, _.toArray(arguments));
  });

  butler.on('exit', function() {
    log('info', ['exiting...']);
  });

  log('info', ['starting...']);
};
