{EventEmitter} = require 'events'
WebSocket      = require 'ws'

# Create a Client that connects to a remote server over a websocket.
module.exports = class Client extends EventEmitter
  constructor: (url, protocols) ->
    @ws = new WebSocket url, protocols
    @nextId = 0
    @requests = {}

    @ws.onopen = => @emit 'open'

    @ws.onclose = (event) =>
      try
        requests = @requests
        @requests = {}
        for own _, callback of requests
          callback? new Error 'WebSocket closed'
      catch err
        @emit 'error', err
      @emit 'close', event.code, event.reason

    @ws.onmessage = (event) =>
      try
        message = JSON.parse event.data
        if message.event?
          name = message.event
          delete message.event
          @emit 'event', name, message
        else
          {id, error, result} = message
          callback = @requests[id]
          delete @requests[id]
          callback? (new Error error.message if error?), result
      catch err
        @emit 'error', err

    @ws.onerror = => @emit 'error', new Error 'WebSocket error'

  # Close the connection. The Client will try to reconnect.
  close: (code, reason) -> @ws.close code, reason

  # Asynchronosly send a JSON-RPC request.
  request: (method, args, callback) ->
    requestId = @nextId++
    @requests[requestId] = callback
    @ws.send JSON.stringify
      jsonrpc: '2.0'
      id: requestId
      method: method
      params: args
