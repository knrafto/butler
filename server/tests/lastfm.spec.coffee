proxyquire = require 'proxyquire'

butler     = require '../butler'
request    = require './mock-request'
api        = proxyquire '../api', request: request
start      = proxyquire '../services/lastfm', api: api

describe 'lastfm', ->
  config = key: 'xxx'

  beforeEach -> start config

  afterEach ->
    request.flush()
    butler.reset()

  describe 'albumInfo', ->
    it 'should fetch album info', (done) ->
      response = baz: 42
      request.expect 'http://ws.audioscrobbler.com/2.0/\
        ?method=album.getInfo&album=foo&artist=bar&api_key=xxx&format=json'
      .respond response

      butler.call 'lastfm.albumInfo', 'foo', 'bar'
      .then (data) ->
        expect(data).toEqual response
        done()

