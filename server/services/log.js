var winston = require('winston');
var _ = require('underscore');

var butler = require('../butler');

/**
 * @module log A service that listens to log events and logs them to a file
 * or the console.
 */
module.exports = function(config) {
  config = config || {};

  var transports = [];
  if (config.console) {
    transports.push(new winston.transports.Console({
      level: config.console.level
    }));
  }
  if (config.file) {
    transports.push(new winston.transports.File({
      level: config.file.level,
      filename: config.file.filename
    }));
  }

  var logger = new winston.Logger({
    transports: transports
  });

  butler.on('log', function() {
    var log = _.bind(logger.log, logger, this.suffix);
    log.apply(null, arguments);
  });

  butler.on('exit', function() {
    logger.info('EXITING');
  });

  logger.info('STARTING');
};
