Q                   = require 'q'

butler              = require '../butler'
{Client, Reconnect} = require '../../common'

module.exports = (config) ->
  client = null

  reconnect = new Reconnect ->
    client = new Client config.url

    client.on 'open', ->
      reconnect.success()
      butler.emit 'mopidy.open'

    client.on 'close', (code, message) ->
      reconnect.retry()
      butler.emit 'mopidy.close', code, message

    client.on 'error', (err) ->
      client.close()
      reconnect.retry()
      butler.emit 'log.error', 'mopidy', err

    client.on 'event', (event, data) -> butler.emit "mopidy.#{event}", data

  butler.register 'mopidy', (args...) ->
    try
      deferred = Q.defer()
      client.request "core.#{@suffix}", args, (err, result) ->
        if err then deferred.reject err else deferred.resolve result
      deferred.promise
    catch err
      Q.reject err
