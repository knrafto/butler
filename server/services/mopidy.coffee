Q                = require 'q'

butler           = require '../butler'
{Action, Client} = require '../../common'

module.exports = (config) ->
  client = null

  connect = new Action ->
    client?.close()
    client = new Client config.url

    client.on 'open', ->
      butler.emit 'mopidy.open'

    client.on 'close', (code, message) ->
      butler.emit 'mopidy.close', code, message
      connect.callLater 2000

    client.on 'error', (err) ->
      butler.emit 'log.error', 'mopidy', err
      connect.callLater 2000

    client.on 'event', (event, data) ->
      butler.emit "mopidy.#{event}", data

  connect.callNow()

  butler.register 'mopidy', (args...) ->
    method = @suffix
    Q.Promise (resolve, reject) ->
      client.request "core.#{method}", args, (err, result) ->
        if err? then reject err else resolve result
