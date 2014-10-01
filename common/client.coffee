{EventEmitter} = require 'events'

WebSocket = require 'ws'

# Create a Client that connects to a remote server over a websocket
module.exports = class Client extends EventEmitter
  constructor: ->
    @readyState = WebSocket.CLOSED
    @ws = null

    @nextId = 0
    @requests = {}

  # Open the connection on the given url and protocols, closing any previous
  # connection. Upon a successful connection, the 'open' event will fire.
  open: (url) ->
    @close()

    @ws = new WebSocket url
    @readyState = WebSocket.CONNECTING

    @ws.onopen = =>
      @readyState = WebSocket.OPEN
      @emit 'open'

    @ws.onclose = (event) =>
      @readyState = WebSocket.CLOSED
      @ws = null
      for own _, callback of @requests
        callback new Error 'WebSocket closed'
      @requests = {}
      @emit 'close', event.code, event.reason

    @ws.onmessage = (event) =>
      try
        message = JSON.parse event.data
        if message.event?
          @emit 'event', message.event, message
        else
          callback = @requests[message.id]
          error = message.error and new Error message.error.message
          callback error, message.result if callback
      catch err
        @emit 'error', err

    @ws.onerror = =>
      @emit 'error', new Error 'WebSocket error'

    return

  # Close the connection, if it exists. This will cancel any pending requests
  # and fire the 'close' event. The connection will not try to reconnect.
  close: (code, reason) =>
    return unless @ws?
    @readyState = WebSocket.CLOSING
    @ws.close code, reason
    return

  # Asynchronosly send a JSON-RPC request.
  request: (method, args, callback) ->
    unless @readyState is WebSocket.OPEN
      throw new Error 'Client not connected'
    requestId = @nextId++
    @requests[requestId] = callback
    @ws.send JSON.stringify
      jsonrpc: '2.0'
      id: requestId
      method: method
      params: args
    return
