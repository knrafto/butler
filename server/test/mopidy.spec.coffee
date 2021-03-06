assert         = require 'assert'
{EventEmitter} = require 'events'

rewire         = require 'rewire'
sinon          = require 'sinon'

Butler         = require '../../common/butler'

class Client extends EventEmitter
  @client = null

  constructor: ->
    @requests = {}
    Client.client = this

  open: (@url) -> Client.clients[@url] = this

  connect: -> @emit 'open'

  close: -> @emit 'close'

  request: (method, args, callback) ->
    fn = @requests[method]
    try
      result = fn args...
    catch err
    callback err, result

  respond: (method, fn) ->
    @requests[method] = fn

start = rewire '../services/mopidy'
start.__set__ 'Client', Client

describe 'mopidy', ->
  url = 'ws://example.com'
  butler = null
  client = null
  clock = null

  beforeEach ->
    butler = new Butler
    start butler, url: url
    client = Client.client

  it 'should open a connection to the mopidy server', ->
    butler.on 'mopidy.connect', ->
      assert.equal client.url, url

  it 'should emit "mopidy.connect" when opened', (done) ->
    butler.on 'mopidy.connect', done
    client.connect()

  it 'should emit "mopidy.disconnect" when closed', (done) ->
    butler.on 'mopidy.disconnect', done
    client.close()

  it 'should forward requests', (done) ->
    client.respond 'core.test', (args) -> args
    butler.call 'mopidy.test', 42
      .then (data) ->
        (expect data).toEqual 42
        done()

  it 'should forward errors', (done) ->
    client.respond 'core.test', -> throw new Error 'bam'
    butler.call 'mopidy.test', 42
      .then null, done

  it 'should forward mopidy events', (done) ->
    args = foo: 42
    butler.on 'mopidy.test', (data) ->
      assert.equal data, args
      done()
    client.emit 'event', 'test', args
