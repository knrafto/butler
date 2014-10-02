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
      (handle request).done (data) -> socket.send data

  butler.on '', (args...) ->
    return if @name.match /^log\./ # don't send log events
    event = JSON.stringify
      event: @name
      params: args
    socket.send event for socket in connections
