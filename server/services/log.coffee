winston = require 'winston'

butler  = require '../butler'

capitalize = (str) -> str[0].toUpperCase() + str[1...]

# @module log A service that listens to log events and logs them to a file
# or the console.
module.exports = (config = {}) ->
  winston.remove winston.transports.Console
  for own name, options of config
    winston.add winston.transports[capitalize name], options

  butler.on 'log', (args...) -> winston.log(@suffix, args...)
