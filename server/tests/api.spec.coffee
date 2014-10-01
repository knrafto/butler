server = do ->
  class Server
    constructor: ->
      @expectations = {}

    expect: (url, data, statusCode, err) ->
      @expectations[url] =
        statusCode: statusCode || 200
        error: err
        data: data

    respond: (url, callback) ->
      response = @expectations[url]
      delete @expectations[url]
      throw new Error "Unexpected request #{url}" unless response
      callback response.error, (statusCode: response.statusCode), response.data

    flush: ->
      expect(@expectations).toEqual {}
      @expectations = {}

  return new Server

request = (options, callback) ->
  throw new Error 'Not a JSON request' unless options.json
  server.respond options.url, callback

require 'request'
require.cache[require.resolve 'request'].exports = request
API = require '../api'
delete require.cache[require.resolve 'request']
delete require.cache[require.resolve '../api']

describe "API", ->
  api = null
  response = result: 42

  beforeEach ->
    api = new API
      url: "http://example.com"
      params: key: "foo"
      max: 3

  afterEach -> server.flush()

  it "should request JSON data", (done) ->
    server.expect "http://example.com?key=foo", response
    api.get().then (data) ->
      expect(data).toBe response
      done()

  it "should encode URL parameters", (done) ->
    server.expect "http://example.com?value=bar%20baz&key=foo", response
    api.get(value: "bar baz").then (data) ->
      expect(data).toBe response
      done()

  it "should cache results in an LRU cache", (done) ->
    server.expect "http://example.com?key=foo", response
    api.get().then (data) ->
      expect(data).toBe response
      api.get().then (data) ->
        expect(data).toBe response
        done()

  it "should reject on error", (done) ->
    server.expect "http://example.com?key=foo", response, 200, new Error()
    api.get().then `undefined`, (err) ->
      expect(err).toBeTruthy()
      done()

  it "should reject on non-200 response", (done) ->
    server.expect "http://example.com?key=foo", response, 404
    api.get().then `undefined`, (err) ->
      expect(err).toBeTruthy()
      done()
