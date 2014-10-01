{EventEmitter} = require 'events'
WebSocket      = require 'ws'

# Create a Client that connects to a remote server over a websocket
module.exports = class Client extends EventEmitter
  constructor: ->
    @ws = null
    @nextId = 0
    @requests = {}

  # Open the connection on the given url and protocols.
  # Upon a successful connection, the 'open' event will fire.
  open: (url) ->
    throw new Error 'Client not closed' if @ws?
    @ws = new WebSocket url

    @ws.onopen = => @emit 'open'

    @ws.onclose = (event) =>
      @ws = null
      for own _, callback of @requests
        callback new Error 'WebSocket closed'
      @requests = {}
      @emit 'close', event.code, event.reason

    @ws.onmessage = (event) =>
      try
        message = JSON.parse event.data
        {event, id, error, result} = message
        if event?
          delete message.event
          @emit 'event', event, message
        else
          callback = @requests[id]
          delete @requests[id]
          if callback?
            error = new Error error.message if error?
            callback error, result
      catch err
        @emit 'error', err

    @ws.onerror = => @emit 'error', new Error 'WebSocket error'

    return

  # Close the connection, if it exists. This will cancel any pending requests
  # and fire the 'close' event. The connection will not try to reconnect.
  close: (code, reason) => @ws.close code, reason if @ws?

  # Asynchronosly send a JSON-RPC request.
  request: (method, args, callback) ->
    unless @ws and @ws.readyState is WebSocket.OPEN
      throw new Error 'Client not connected'
    requestId = @nextId++
    @requests[requestId] = callback
    @ws.send JSON.stringify
      jsonrpc: '2.0'
      id: requestId
      method: method
      params: args
