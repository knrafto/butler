nock   = require 'nock'

butler = require '../butler'
start  = require '../services/lastfm'

describe 'lastfm', ->
  config = key: 'xxx'
  scope = null

  beforeEach ->
    start config
    scope = nock('http://ws.audioscrobbler.com:80')

  afterEach ->
    scope.done()
    nock.restore()
    butler.reset()

  describe 'albumInfo', ->
    it 'should fetch album info', (done) ->
      response = album: 42
      scope.get '/2.0?album=foo&artist=bar\
          &method=album.getInfo&api_key=xxx&format=json'
        .reply 200, response

      butler.call 'lastfm.albumInfo', 'foo', 'bar'
        .then (data) ->
          (expect data).toEqual response
        .then ->
          butler.call 'lastfm.albumInfo', 'foo', 'bar'
        .then (data) ->
          (expect data).toEqual response
          done()
