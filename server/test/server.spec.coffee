assert         = require 'assert'
{EventEmitter} = require 'events'

Q              = require 'q'
rewire         = require 'rewire'

Butler         = require '../../common/butler'

class Server extends EventEmitter
  @server = null

  constructor: (@options) ->
    Server.server = this

class Socket extends EventEmitter
  constructor: (server) ->
    @messages = []
    server.emit 'connection', this

  close: ->
    @emit 'close'

  message: (data) ->
    @emit 'message', JSON.stringify data

  send: (data) ->
    @messages.push JSON.parse data
    @emit 'send', data

start = rewire '../services/server'
start.__set__ 'Server', Server

describe 'server', ->
  butler = null
  server = null
  config =
    host: 'example.com'
    port: 54010

  beforeEach ->
    butler = new Butler
    start butler, config
    server = Server.server

  it 'should start a server', ->
    assert.equal server.options, config

  describe 'events', ->
    it 'should be sent to all open connections', ->
      sockets = new Socket server for _ in [1..3]

      butler.emit 'foo', 1, 2
      butler.emit 'bar', 3, 4
      for socket in sockets
        assert.deepEqual socket.messages, [
          event: 'foo'
          params: [1, 2]
        ,
          event: 'bar'
          params: [3, 4]
        ]
      return

    it 'should not be sent to closed connections', ->
      socket = new Socket server
      butler.emit 'foo', 1, 2
      socket.close()
      butler.emit 'bar', 3, 4
      assert.deepEqual socket.messages, [
        event: 'foo'
        params: [1, 2]
      ]

  describe 'requests', ->
    it 'should be responded to', (done) ->
      socket = new Socket server
      butler.register 'foo', (a, b) -> a + b

      socket.message
        id: 10
        method: 'foo'
        params: [1, 2]

      socket.on 'send', ->
        assert.deepEqual socket.messages, [
          id: 10
          error: null
          result: 3
        ]
        done()

    it 'should handle errors', (done) ->
      socket = new Socket server
      butler.register 'foo', -> throw new Error 'bam'

      socket.message
        id: 10
        method: 'foo'
        params: [1, 2]

      socket.on 'send', (data) ->
        assert.deepEqual socket.messages, [
          id: 10
          error:
            code: 0
            message: 'bam'
          result: null
        ]
        done()

    it 'should wait for promises', (done) ->
      socket = new Socket server
      butler.register 'foo', (a, b) -> Q(a + b)

      socket.message
        id: 10
        method: 'foo'
        params: [1, 2]

      socket.on 'send', ->
        assert.deepEqual socket.messages, [
          id: 10
          error: null
          result: 3
        ]
        done()

    it 'should wait for promises with errors', (done) ->
      socket = new Socket server
      butler.register 'foo', -> Q.reject new Error 'bam'

      socket.message
        id: 10
        method: 'foo'
        params: [1, 2]

      socket.on 'send', ->
        assert.deepEqual socket.messages, [
          id: 10
          error:
            code: 0
            message: 'bam'
          result: null
        ]
        done()
