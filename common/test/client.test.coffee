assert = require 'assert'

rewire = require 'rewire'

class WebSocket
  @instance = null

  CONNECTING: 0
  OPEN: 1
  CLOSING: 2
  CLOSED: 3

  constructor: (@url, @protocols)  ->
    @readyState = @CONNECTING
    @sent = []
    WebSocket.instance = this

  open: ->
    @readyState = @OPEN
    @onopen()

  close: (code, reason) ->
    unless @readyState in [@CLOSING, @CLOSED]
      @readyState = @CLOSED
      @onclose code: code, reason: reason

  error: ->
    @onerror()

  send: (data) ->
    unless @readyState is @OPEN
      throw new Error 'WebSocket is not open'
    @sent.push JSON.parse data

  receive: (data) ->
    @onmessage data: JSON.stringify data

Client = rewire '../client'
Client.__set__ 'WebSocket', WebSocket

describe 'Client', ->
  url = 'ws://example.com'
  protocols = []

  client = null
  socket = null

  beforeEach ->
    client = new Client url, protocols
    socket = WebSocket.instance

  it 'should open a new connection', ->
    assert.equal socket.url, url
    assert.equal socket.protocols, protocols

  it 'should emit "open" when a connection is open', (done) ->
    client.on 'open', -> done()
    socket.open()

  it 'should emit "close" when a pending connection is closed', (done) ->
    client.on 'close', -> done()
    socket.close()

  it 'should emit "close" when a connection is closed', (done) ->
    socket.open()
    client.on 'close', -> done()
    socket.close()

  it 'should emit "error" on error', (done) ->
    client.on 'error', -> done()
    socket.error()

  describe '#close', ->
    it 'should close a pending connection', ->
      client.close()
      assert.equal socket.readyState, WebSocket::CLOSED

    it 'should close an open connection', ->
      socket.open()
      client.close()
      assert.equal socket.readyState, WebSocket::CLOSED

    it 'should emit "close" when a pending connection is closed', (done) ->
      client.on 'close', done
      client.close()

    it 'should emit "close" when a connection is closed', (done) ->
      socket.open()
      client.on 'close', done
      client.close()

    it 'should do nothing if closed', ->
      debugger
      client.close()
      client.on 'close', -> throw new Error 'Closed twice'
      client.close()
      assert.equal socket.readyState, WebSocket::CLOSED

  describe '#request', ->
    it 'should send requests', ->
      socket.open()
      client.request 'foo', [1, 2], ->
      client.request 'bar', [3, 4], ->
      assert.deepEqual socket.sent, [
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
      assert.throws -> client.request 'foo', [1, 2], ->

    it 'should throw when closed', ->
      socket.close()
      assert.throws -> client.request 'foo', [1, 2], ->

    it 'should respond with success', (done) ->
      socket.open()
      client.request 'foo', [1, 2], (err, result) ->
        assert.equal err, null
        assert.equal result, 'result'
        done()
      client.request 'bar', [3, 4], ->
      socket.receive
        id: 1
        error: code: 0, message: 'bam'
        result: null
      socket.receive
        id: 0
        error: null
        result: 'result'

    it 'should respond with error', (done) ->
      socket.open()
      client.request 'foo', [1, 2], (err, result) ->
        assert.notEqual err, null
        done()
      client.request 'bar', [3, 4], ->
      socket.receive
        id: 0
        error:
          code: 0
          message: 'oops'
        result: null

    it 'should respond with error when closed', (done) ->
      socket.open()
      client.request 'foo', [1, 2], (err, result) ->
        assert.notEqual err, null
        done()
      socket.close()

  it 'should emit events', (done) ->
    socket.open()
    client.on 'event', (name, data) ->
      assert.equal name, 'foo',
      assert.deepEqual data, bar: 42, baz: 27
      done()
    socket.receive event: 'foo', bar: 42, baz: 27
