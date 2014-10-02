{EventEmitter} = require 'events'

rewire         = require 'rewire'
sinon          = require 'sinon'

butler         = require '../butler'

class Client extends EventEmitter
  @clients = []

  constructor: ->
    @requests = {}

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
  client = null
  clock = null

  beforeEach ->
    start url: url
    client = Client.clients[url]

  afterEach -> butler.reset()

  it 'should open a connection to the mopidy server', ->
    (expect client.url).toEqual url

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
      (expect data).toEqual args
      done()
    client.emit 'event', 'test', args
