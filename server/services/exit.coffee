butler = require '../butler'

# @module exit A service that fires an 'exit' event when the server exists,
# and logs exit conditions.
module.exports = ->
  process.on 'exit', (code) ->
    butler.emit 'exit', code

  process.on 'SIGINT', ->
    butler.emit 'log.info', 'SIGINT'
    process.exit 0

  process.on 'SIGTERM', ->
    butler.emit 'log.info', 'SIGTERM'
    process.exit 0

  process.on 'uncaughtException', (err) ->
    console.log err.stack
    butler.emit 'log.fatal', err
    process.exit 1
