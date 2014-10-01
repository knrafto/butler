rewire = require 'rewire'

socket = null

class WebSocket
  constructor: (url, protocols)  ->
    @url = url
    @sent = []
    @closed = false
    socket = @

  open: ->
    @onopen?()

  close: (code, reason) ->
    @closed = true
    @onclose? code: code, reason: reason

  send: (data)  ->
    @sent.push JSON.parse data

  receive: (data)  ->
    @onmessage? data: JSON.stringify data

  error: ->
    @onerror?()

do ->
  for state, i in ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED']
    WebSocket.prototype[state] = WebSocket[state] = i

Client = rewire '../client'
Client.__set__ 'WebSocket', WebSocket

describe 'Client', ->
  client = null
  url = 'ws://example.com'

  beforeEach ->
    client = new Client
    client.open url

  describe 'open', ->
    it 'should attempt to open a new connection', ->
      expect(socket.url).toEqual url

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

    it 'should emit "close" on failure before opening', (done) ->
      client.on 'close', (code, reason) ->
        expect(code).toEqual 1006
        expect(reason).toEqual 'reason'
        done()
      socket.close 1006, 'reason'

    it 'should emit "close" on failure after opening', (done) ->
      socket.open()
      client.on 'close', (code, reason) ->
        expect(code).toEqual 1006
        expect(reason).toEqual 'reason'
        done()
      socket.close 1006, 'reason'

    it 'should close any previous connection before opening', (done) ->
      client.on 'close', done
      client.open url

    it 'should close any previous connection after opening', (done) ->
      socket.open()
      client.on 'close', done
      client.open url

  describe 'close', ->
    it 'should close the connection', ->
      client.close()
      expect(socket.closed).toBe true

      client.open url
      socket.open()
      client.close()
      expect(socket.closed).toBe true

    it 'should emit "close" before opening', (done) ->
      client.on 'close', done
      client.close()

    it 'should emit "close" after opening', (done) ->
      socket.open()
      client.on 'close', done
      client.close()

    it 'should do nothing when not open', ->
      client.close()
      client.on 'close', ->
        throw new Error 'Client closed twice'
      client.close()

    it 'should do nothing when closing', ->
      socket.open()
      client.close()
      client.on 'close', ->
        throw new Error 'Client closed twice'
      client.close()

  describe 'request', ->
    it 'should send numbered requests to the server', ->
      socket.open()
      client.request 'foo', [1, 2], ->
      client.request 'bar', (3: 4), ->
      expect(socket.sent).toEqual [
        jsonrpc: '2.0'
        id: 0
        method: 'foo'
        params: [1, 2]
      ,
        jsonrpc: '2.0'
        id: 1
        method: 'bar'
        params: 3: 4
      ]

    it 'should call the callback on success', (done) ->
      socket.open()

      client.request 'foo', [1, 2], (err, result) ->
        expect(err).toBeFalsy()
        expect(result).toBe 'result'
        done()

      client.request 'bar', (3: 4), ->

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

      client.request 'bar', 3: 4, ->

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

      client.request 'bar', 3: 4, ->

      socket.close()

  it 'should emit events', (done) ->
    socket.open()

    data =
      event: 'foo',
      params: [1, 2]

    client.on 'event', (name, event) ->
      expect(name).toEqual 'foo'
      expect(event).toEqual data
      done()

    socket.receive data
