Q        = require 'q'
{Server} = require 'ws'

butler   = require '../butler'

remove = (lst, e) ->
  i = lst.indexOf e
  lst.splice i, 1 unless i is -1

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
  connections = []
  server = new Server config

  server.on 'error', (err) -> butler.emit 'log.error', 'server', err

  server.on 'connection', (socket) ->
    connections.push socket
    socket.on 'close', -> remove connections, socket
    socket.on 'message', (request) ->
      butler.emit 'log.debug', 'request', request
      (handle request).done (response) ->
        butler.emit 'log.debug', 'response', response
        socket.send response

  butler.on '', (args...) ->
    return if @name.match /^log\./ # don't send log events
    event = JSON.stringify
      event: @name
      params: args
    butler.emit 'log.debug', 'event', event
    socket.send event for socket in connections
