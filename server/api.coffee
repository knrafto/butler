LRU     = require 'lru-cache'
Q       = require 'q'
request = require 'request'
url     = require 'url'

# A LRU cache of API results.
module.exports = class API
  constructor: (options) ->
    @url = options.url
    @params = options.params
    @cache = new LRU options

  # Get JSON from a url.
  get: (params) ->
    params ?= {}
    for own k, v of @params
      params[k] = v
    requestUrl = @url + url.format query: params

    cached = @cache.get requestUrl
    return Q cached if cached

    deferred = Q.defer()
    request
      url: requestUrl
      json: true
    , (err, response, body) =>
      if err
        deferred.reject err
      else if response.statusCode < 200 or response.statusCode > 299
        deferred.reject new Error "#{response.statusCode} #{requestUrl}"
      else
        @cache.set requestUrl, body
        deferred.resolve body
    return deferred.promise
