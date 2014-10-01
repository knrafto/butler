proxyquire = require 'proxyquire'

request    = require './mock-request'
API        = proxyquire '../api', request: request

describe 'API', ->
  api = null
  response = result: 42

  beforeEach ->
    api = new API
      url: 'http://example.com'
      params: key: 'foo'
      max: 3

  afterEach -> request.flush()

  it 'should request JSON data', (done) ->
    request.expect 'http://example.com?key=foo'
    .respond response
    api.get().then (data) ->
      expect(data).toBe response
      done()

  it 'should encode URL parameters', (done) ->
    request.expect 'http://example.com?value=bar%20baz&key=foo'
    .respond response
    api.get(value: 'bar baz').then (data) ->
      expect(data).toBe response
      done()

  it 'should cache results in an LRU cache', (done) ->
    request.expect 'http://example.com?key=foo'
    .respond response
    api.get().then (data) ->
      expect(data).toBe response
      api.get().then (data) ->
        expect(data).toBe response
        done()

  it 'should reject on error', (done) ->
    request.expect 'http://example.com?key=foo'
    .error new Error
    api.get().then `undefined`, (err) ->
      expect(err).toBeTruthy()
      done()

  it 'should reject on non-200 response', (done) ->
    request.expect 'http://example.com?key=foo'
    .respond response, 404
    api.get().then `undefined`, (err) ->
      expect(err).toBeTruthy()
      done()
