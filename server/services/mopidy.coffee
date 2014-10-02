Q      = require 'q'

butler = require '../butler'
Client = require '../../common/client'

module.exports = (config) ->
  client = new Client
  reconnectTimeout = null

  client.open config.url

  butler.register 'mopidy', (args...) ->
    try
      deferred = Q.defer()
      client.request "core.#{@suffix}", args, (err, result) ->
        if err then deferred.reject err else deferred.resolve result
      deferred.promise
    catch err
      Q.reject err

  client.on 'open', ->
    clearTimeout reconnectTimeout
    butler.emit 'mopidy.connect'

  client.on 'close', (code, message) ->
    butler.emit 'mopidy.disconnect', code, message
    clearTimeout reconnectTimeout
    reconnectTimeout = setTimeout (-> client.open config.url), 8000

  client.on 'error', (errno) -> butler.emit 'log.error', 'mopidy', errno

  client.on 'event', (event, data) -> butler.emit "mopidy.#{event}", data
