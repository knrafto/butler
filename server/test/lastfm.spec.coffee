nock   = require 'nock'

Butler = require '../../common/butler'
start  = require '../services/lastfm'

describe 'lastfm', ->
  butler = null
  config = key: 'xxx'
  scope = null

  beforeEach ->
    butler = new Butler
    start butler, config
    scope = nock 'http://ws.audioscrobbler.com:80'

  afterEach ->
    scope.done()
    nock.restore()

  describe 'albumInfo', ->
    it 'should fetch album info', (done) ->
      response = album: 42
      scope.get '/2.0/?album=foo&api_key=xxx&artist=bar\
        &format=json&method=album.getInfo'
      .reply 200, response

      butler.call 'lastfm.album.getInfo',
        album: 'foo'
        artist: 'bar'
      .then (data) ->
        assert.deepEqual data, response
        done()
