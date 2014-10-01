winston = require 'winston'

butler  = require '../butler'

# @module log A service that listens to log events and logs them to a file
# or the console.
module.exports = (config) ->
  config ?= {}
  transports = []

  if config.console?
    transports.push new winston.transports.Console
      level: config.console.level
  if config.file?
    transports.push new winston.transports.File
      level: config.file.level
      filename: config.file.filename

  logger = new winston.Logger transports: transports

  butler.on 'log', (args...) -> logger.log(@suffix, args...)

  butler.on 'exit', -> logger.info 'EXITING'

  logger.info 'STARTING'
