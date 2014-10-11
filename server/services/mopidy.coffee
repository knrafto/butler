Q                = require 'q'

{Action, Client} = require '../../common'

module.exports = (butler, config) ->
  client = null

  connect = new Action ->
    client?.close()
    client = null

    try
      client = new Client config.url
    catch err
      butler.emit 'error', err
      return

    client.on 'open', ->
      butler.emit 'mopidy.open'

    client.on 'close', (code, reason) ->
      butler.emit 'mopidy.close'
      connect.run 2000

    client.on 'error', (err) ->
      butler.emit 'error', err
      connect.run 2000

    client.on 'event', (name, event) ->
      butler.emit "mopidy.#{name}", event

  connect.run 0

  butler.register 'mopidy', (args...) ->
    method = @suffix
    Q.Promise (resolve, reject) ->
      throw new Error 'Client not opened' unless client?
      client.request "core.#{method}", args, (err, result) ->
        if err? then reject err else resolve result
