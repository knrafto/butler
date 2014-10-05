{EventEmitter} = require 'events'
WebSocket      = require 'ws'

# A client that connects to a remote server over a websocket.
module.exports = class Client extends EventEmitter
  constructor: (url, protocols) ->
    @ws = new WebSocket url, protocols
    @nextId = 0
    @requests = {}

    @ws.onopen = =>
      @emit 'open'

    @ws.onclose = (event) =>
      try
        error = new Error 'WebSocket closed'
        requests = @requests
        @requests = {}
        for own _, callback of requests
          callback error, null
      catch err
        @emit 'error', err
      @emit 'close', event.code, event.reason

    @ws.onerror = =>
      @emit 'error', new Error 'WebSocket error'

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

  close: ->
    @ws.close()

  # Asynchronosly send a JSON-RPC request.
  request: (method, args, callback) ->
    unless @ws.readyState is WebSocket::OPEN
      throw new Error "WebSocket is not open"
    requestId = @nextId++
    @requests[requestId] = callback
    @ws.send JSON.stringify
      jsonrpc: '2.0'
      id: requestId
      method: method
      params: args
