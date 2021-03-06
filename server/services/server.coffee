Q        = require 'q'
{Server} = require 'ws'

remove = (lst, e) ->
  i = lst.indexOf e
  lst.splice i, 1 unless i is -1

# @module server A service that responds to JSON-RPC requests and emits
# events over a WebSocket.
module.exports = (butler, config) ->
  connections = []
  server = new Server config

  server.on 'error', (err) ->
    butler.emit 'error', err

  server.on 'connection', (socket) ->
    connections.push socket

    socket.on 'close', ->
      remove connections, socket

    socket.on 'message', (request) ->
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
      .then (response) ->
        socket.send JSON.stringify response
      .catch (err) ->
        butler.emit 'error', err

  butler.on '', (args...) ->
    try
      event = JSON.stringify
        event: @name
        params: args
      socket.send event for socket in connections
    catch err
      butler.emit 'error', err
