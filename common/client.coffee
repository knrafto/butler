{EventEmitter} = require 'events'
WebSocket      = require 'ws'

# Create a Client that connects to a remote server over a websocket.
# To query a client's state, use the readyState property. It is one
# of:
# * 'connecting'
# * 'open'
# * 'closed'
#
# Instances also emit the following events:
# * 'open'
# * 'close'
# * 'error'
module.exports = class Client extends EventEmitter
  constructor: (options = {}) ->
    {@reconnectInterval, @reconnectIntervalMax, @timeout} = options
    @reconnectInterval ?= 1000
    @reconnectIntervalMax ?= 8000
    @timeout ?= 2000

    @readyState = 'closed'
    @ws = null
    @reconnectWait = @reconnectInterval
    @reconnectTimeout = null # (possibly) active if 'closed'

    @nextId = 0
    @requests = {}

  # Attempt to open a new connection, closing any previous connection.
  # If the connection attempt fails, the Client will try to reconnect.
  open: (url) ->
    @destroy()

    @url = url if url?
    throw new Error 'No URL' unless @url?

    @readyState = 'connecting'
    @ws = new WebSocket url
    clearTimeout @reconnectTimeout

    timeoutTimeout = setTimeout (=> @ws.close()), @timeout

    @ws.onopen = =>
      clearTimeout timeoutTimeout
      @readyState = 'open'
      @reconnectWait = @reconnectInterval
      clearTimeout @reconnectTimeout
      @emit 'open'

    @ws.onclose = (event) =>
      clearTimeout timeoutTimeout
      @readyState = 'closed'
      @close event.code, event.reason

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
  close: (code, reason) ->
    @destroy code, reason
    @reconnectWait = Math.max @reconnectIntervalMax, 2 * @reconnectWait
    @reconnectTimeout = setTimeout (=> @open()), @reconnectWait

  # Close the connection. The Client will not try to reconnect.
  destroy: (code, reason) ->
    unless @readyState is 'closed'
      @ws.close code, reason
      @emit 'close', code, reason

    @ws = null
    clearTimeout @reconnectTimeout

    try
      requests = @requests
      @requests = {}
      for own _, callback of requests
        callback? new Error 'WebSocket closed'
    catch err
      @emit 'error', err

  # Asynchronosly send a JSON-RPC request.
  request: (method, args, callback) ->
    unless @readyState is 'open'
      throw new Error 'Client not connected'
    requestId = @nextId++
    @requests[requestId] = callback
    @ws.send JSON.stringify
      jsonrpc: '2.0'
      id: requestId
      method: method
      params: args
