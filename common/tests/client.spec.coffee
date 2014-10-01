rewire = require 'rewire'

class WebSocket
  @sockets: {}

  @CONNECTING: 0
  @OPEN: 1
  @CLOSING: 2
  @CLOSED: 3

  constructor: (@url, @protocols)  ->
    @readyState = WebSocket.CONNECTING
    @sent = []
    WebSocket.sockets[@url] = @

  open: ->
    @readyState = WebSocket.OPEN
    @onopen?()

  close: (code, reason) ->
    @readyState = WebSocket.CLOSED
    delete WebSocket.sockets[@url]
    @onclose? code: code, reason: reason

  send: (data) -> @sent.push JSON.parse data

  receive: (data) -> @onmessage? data: JSON.stringify data

  error: -> @onerror?()

Client = rewire '../client'
Client.__set__ 'WebSocket', WebSocket

describe 'Client', ->
  client = null
  socket = null
  url = 'ws://example.com'

  beforeEach ->
    client = new Client
    client.open url
    socket = WebSocket.sockets[url]

  describe 'open', ->
    it 'should attempt to open a new connection', ->
      (expect socket.url).toEqual url

    it 'should emit "open" on success', (done) ->
      client.on 'open', done
      socket.open()

    it 'should emit "error" on error before opening', (done) ->
      client.on 'error', done
      socket.error()

    it 'should emit "error" on error after opening', (done) ->
      socket.open()
      client.on 'error', done
      socket.error()

    it 'should emit "close" on closure before opening', (done) ->
      client.on 'close', (code, reason) ->
        (expect code).toEqual 1006
        (expect reason).toEqual 'reason'
        done()
      socket.close 1006, 'reason'

    it 'should emit "close" on closure after opening', (done) ->
      socket.open()
      client.on 'close', (code, reason) ->
        (expect code).toEqual 1006
        (expect reason).toEqual 'reason'
        done()
      socket.close 1006, 'reason'

    it 'should throw if a connection is opening', ->
      expect(-> client.open url).toThrow()

    it 'should throw if a connection is already open', ->
      socket.open()
      expect(-> client.open url).toThrow()

    it 'should reopen the connection if closed', (done) ->
      otherUrl = 'ws://foo.org'
      client.close()
      client.open otherUrl
      client.on 'open', done
      WebSocket.sockets[otherUrl].open()

  describe 'close', ->
    it 'should close the connection', ->
      client.close()
      (expect socket.readyState).toEqual WebSocket.CLOSED

    it 'should emit "close" when closed before opening', (done) ->
      client.on 'close', done
      client.close()

    it 'should emit "close" when closed after opening', (done) ->
      socket.open()
      client.on 'close', done
      client.close()

    it 'should do nothing when not open', ->
      client.close()
      client.on 'close', ->
        throw new Error 'Client closed twice'
      client.close()

  describe 'request', ->
    it 'should send numbered requests to the server', ->
      socket.open()
      client.request 'foo', [1, 2], ->
      client.request 'bar', [3, 4], ->
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

    it 'should call the callback on success', (done) ->
      socket.open()

      client.request 'foo', [1, 2], (err, result) ->
        (expect err).toBeFalsy()
        (expect result).toEqual 'result'
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

    it 'should call the callback on error', (done) ->
      socket.open()

      client.request 'foo', [1, 2], (err, result) ->
        expect(err).toEqual new Error 'oops'
        expect(result).toBe null
        done()
      client.request 'bar', [3, 4], ->

      socket.receive
        id: 0
        error:
          code: 0
          message: 'oops'
        result: null

    it 'should call the callback on close', (done) ->
      socket.open()
      client.request 'foo', [1, 2], (err, result) ->
        expect(err).toBeTruthy()
        done()
      client.request 'bar', [3, 4], ->
      socket.close()

  describe 'event', ->
    it 'should emit events', (done) ->
      socket.open()
      client.on 'event', (name, data) ->
        (expect name).toEqual 'foo'
        (expect data).toEqual params: [1, 2]
        done()
      socket.receive event: 'foo', params: [1, 2]
