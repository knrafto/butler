rewire = require 'rewire'

class WebSocket
  @sockets: {}

  CONNECTING: 0
  OPEN: 1
  CLOSING: 2
  CLOSED: 3

  constructor: (@url)  ->
    @readyState = @CONNECTING
    @sent = []
    WebSocket.sockets[@url] = @

  open: ->
    @readyState = @OPEN
    @onopen?()

  close: (code, reason) ->
    unless @readyState is @CLOSED
      @readyState = @CLOSED
      delete WebSocket.sockets[@url]
      @onclose? code: code, reason: reason

  send: (data) -> @sent.push JSON.parse data

  receive: (data) -> @onmessage? data: JSON.stringify data

  error: -> @onerror?()

Client = rewire '../client'
Client.__set__ 'WebSocket', WebSocket

describe 'Client', ->

  beforeEach ->
    @client = new Client
      reconnectInterval: 1000
      reconnectIntervalMax: 4000
      timeout: 1000

    @connect = =>
      url = 'ws://example.com'
      @client.open url
      WebSocket.sockets[url]

    @events = []
    @client.on 'open', => @events.push 'open'
    @client.on 'close', => @events.push 'close'
    @client.on 'error', => @events.push 'error'
    @client.on 'event', (name, data) => @events.push name: name, data: data

  afterEach -> @client.destroy()

  it 'should set default values', ->
    @client = new Client
    (expect @client.reconnectInterval).toEqual 1000
    (expect @client.reconnectIntervalMax).toEqual 8000
    (expect @client.timeout).toEqual 2000

  it 'should initially be closed', ->
    (expect @client.readyState).toEqual 'closed'
    (expect @events).toEqual []

  describe 'open', ->
    it 'should open a new connection', ->
      socket = @connect()
      (expect @client.readyState).toEqual 'connecting'

      socket.open()
      (expect @client.readyState).toEqual 'open'
      (expect @client.url).toEqual socket.url
      (expect @events).toEqual ['open']

    it 'should close an open connection', ->
      socket = @connect()
      socket.open()

      @client.open()
      (expect socket.readyState).toEqual socket.CLOSED
      (expect @events).toEqual ['open', 'close']

    it 'should attempt to reconnect on failure'

    it 'should timeout'

    it 'should attempt to reconnect on timeout'

  describe 'close', ->
    it 'should close an open connection', ->
      socket = @connect()
      socket.open()
      @client.close()
      (expect @client.readyState).toEqual 'closed'
      (expect @events).toEqual ['open', 'close']

    it 'should do nothing if closed', ->
      @client.close()
      (expect @client.readyState).toEqual 'closed'
      (expect @events).toEqual []

    it 'should attempt to reconnect'

  describe 'destroy', ->
    it 'should close an open connection', ->
      socket = @connect()
      socket.open()
      @client.destroy()
      (expect @client.readyState).toEqual 'closed'
      (expect @events).toEqual ['open', 'close']

    it 'should do nothing if closed', ->
      @client.destroy()
      (expect @client.readyState).toEqual 'closed'
      (expect @events).toEqual []

    it 'should not attempt to reconnect'

  describe 'request', ->
    it 'should send requests', ->
      socket = @connect()
      socket.open()
      @client.request 'foo', [1, 2], ->
      @client.request 'bar', [3, 4], ->
      (expect socket.sent).toEqual [
        jsonrpc: '2.0'
        id: 0
        method: 'foo'
        params: [1, 2]
      ,
        jsonrpc: '2.0'
        id: 1
        method: 'bar'
        params: [3, 4]
      ]

    it 'should throw when not open', ->
      socket = @connect()
      expect -> @client.request 'foo', [1, 2], ->
        .toThrow()

    it 'should respond with success', ->
      socket = @connect()
      socket.open()

      responses = []
      @client.request 'foo', [1, 2], (err, result) ->
        responses.push
          error: err
          result: result
      @client.request 'bar', [3, 4], ->

      socket.receive
        id: 1
        error: code: 0, message: 'bam'
        result: null
      socket.receive
        id: 0
        error: null
        result: 'result'

      (expect responses).toEqual [
        error: undefined
        result: 'result'
      ]

    it 'should respond with error', ->
      socket = @connect()
      socket.open()

      responses = []
      @client.request 'foo', [1, 2], (err, result) ->
        responses.push
          error: err
          result: result
      @client.request 'bar', [3, 4], ->

      socket.receive
        id: 0
        error:
          code: 0
          message: 'oops'
        result: null

      (expect responses).toEqual [
        error: new Error 'oops'
        result: null
      ]

    it 'should respond with error when closed', ->
      socket = @connect()
      socket.open()

      responses = []
      @client.request 'foo', [1, 2], (err, result) ->
        responses.push
          error: err
          result: result
      socket.close()

      (expect responses).toEqual [
        error: new Error 'WebSocket closed'
        result: undefined
      ]

    it 'should respond with error when destroyed', ->
      socket = @connect()
      socket.open()

      responses = []
      @client.request 'foo', [1, 2], (err, result) ->
        responses.push
          error: err
          result: result
      @client.destroy()

      (expect responses).toEqual [
        error: new Error 'WebSocket closed'
        result: undefined
      ]

  it 'should emit events', ->
    socket = @connect()
    socket.open()
    socket.receive event: 'foo', params: [1, 2]
    socket.receive event: 'bar', bar: 42, baz: 27
    (expect @events).toEqual [
      'open'
    ,
      name: 'foo'
      data: params: [1, 2]
    ,
      name: 'bar'
      data:
        bar: 42
        baz: 27
    ]
