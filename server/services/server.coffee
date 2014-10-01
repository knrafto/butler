Q        = require 'q'
{Server} = require 'ws'

butler   = require '../butler'

# Asynchronously handle a JSON-RPC request string using the butler.
handle = (request) ->
  Q.try ->
    request = JSON.parse request
    butler.call request.method, request.params...
  .then (result) ->
    result: result
    error: null
    id: request.id
  , (err) ->
    result: null
    error:
      code: 0
      message: err.message
    id: request.id
  .then JSON.stringify

# @module server A service that responds to JSON-RPC requests and emits
# events over a WebSocket.
module.exports = (config) ->
  config ?=
  connections = []
  server = new Server
    host: config.hostname
    port: config.port

  server.on 'error', (err) ->
    butler.emit 'log.error', 'server', err

  server.on 'connection', (socket) ->
    connections.push socket
    socket.on 'close', ->
      i = connections.indexOf socket
      connections.splice i, 1 unless i is -1

    socket.on 'message', (request) ->
      butler.emit 'log.debug', 'server', 'request', request
      handle(request).done (response) ->
        butler.emit 'log.debug', 'server', 'response', response
        socket.send response

  butler.on '', (args...) ->
    return if @name.match /^log\./ # don't send log events
    event = JSON.stringify
      event: @name
      params: args
    butler.emit 'log.debug', 'server', 'event', event
    socket.send event for socket in connections
