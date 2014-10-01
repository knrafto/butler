{EventEmitter} = require 'events'
proxyquire     = require 'proxyquire'
Q              = require 'q'

butler         = require '../butler'

messages = (socket) ->
  for args in socket.send.calls.allArgs()
    expect(args.length).toEqual 1
    JSON.parse args[0]

describe 'server', ->
  ws = null
  server = null
  start = null

  beforeEach ->
    server = new EventEmitter
    ws = Server: jasmine.createSpy('Server').and.returnValue server
    start = proxyquire '../services/server', ws: ws
    start
      hostname: 'localhost'
      port: 54010

  afterEach -> butler.reset()

  it 'should start a server', ->
    expect(ws.Server).toHaveBeenCalledWith
      host: 'localhost'
      port: 54010

  describe 'events', ->
    it 'should be sent to all open connections', ->
      sockets = for _ in [1..3]
        socket = new EventEmitter
        socket.send = jasmine.createSpy 'send'
        server.emit 'connection', socket
        socket

      butler.emit 'foo', 1, 2
      butler.emit 'bar', 3, 4
      for socket in sockets
        expect(messages socket).toEqual [
          event: 'foo'
          params: [1, 2]
        ,
          event: 'bar'
          params: [3, 4]
        ]

    it 'should not be sent to closed connections', ->
      for _ in [1..3]
        socket = new EventEmitter
        socket.send = ->
        server.emit 'connection', socket

      socket = new EventEmitter
      socket.send = jasmine.createSpy 'send'
      server.emit 'connection', socket
      butler.emit 'foo', 1, 2
      socket.emit 'close'
      butler.emit 'bar', 3, 4
      expect(messages socket).toEqual [
        event: 'foo'
        params: [1, 2]
      ]

  describe 'requests', ->
    it 'should be responded to', (done) ->
      socket = new EventEmitter
      server.emit 'connection', socket
      butler.register 'foo', (a, b) -> a + b

      socket.emit 'message', JSON.stringify
        id: 10
        method: 'foo'
        params: [1, 2]

      socket.send = (message) ->
        expect(JSON.parse message).toEqual
          id: 10
          error: null
          result: 3
        done()

    it 'should handle errors', (done) ->
      socket = new EventEmitter
      server.emit 'connection', socket
      butler.register 'foo', -> throw new Error 'bam'

      socket.emit 'message', JSON.stringify
        id: 10
        method: 'foo'
        params: [1, 2]

      socket.send = (message) ->
        expect(JSON.parse message).toEqual
          id: 10
          error:
            code: 0
            message: 'bam'
          result: null
        done()

    it 'should wait for promises', (done) ->
      socket = new EventEmitter
      server.emit 'connection', socket
      butler.register 'foo', (a, b) -> Q(a + b)

      socket.emit 'message', JSON.stringify
        id: 10
        method: 'foo'
        params: [1, 2]

      socket.send = (message) ->
        expect(JSON.parse message).toEqual
          id: 10
          error: null
          result: 3
        done()

    it 'should wait for promises with errors', (done) ->
      socket = new EventEmitter
      server.emit 'connection', socket
      butler.register 'foo', (a, b) -> Q.reject new Error 'bam'

      socket.emit 'message', JSON.stringify
        id: 10
        method: 'foo'
        params: [1, 2]

      socket.send = (message) ->
        expect(JSON.parse message).toEqual
          id: 10
          error:
            code: 0
            message: 'bam'
          result: null
        done()
