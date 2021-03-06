Cache   = require 'lru-cache'
Q       = require 'q'
qs      = require 'qs'
request = require 'request'

extend = (dst, srcs...) ->
  for src in srcs
    for own k, v of src
      dst[k] = v
  dst

buildUrl = (url, params) ->
  return url unless params?
  keys = (k for own k, _ of params).sort()
  parts = for k in keys
    isolate = {}
    isolate[k] = params[k]
    qs.stringify isolate
  if parts.length
    url + (if '?' in url then '&' else '?') + parts.join '&'
  else
    url

get = (url, params, cache) ->
  Q.Promise (resolve, reject) ->
    url = buildUrl url, params
    if cache? && (cached = cache.get url)?
      return resolve cached
    request url: url, json: true, (err, response, data) ->
      if err?
        reject err
      else unless 200 <= (status = response.statusCode) < 300
        reject new Error "#{status} #{url}"
      else
        cache.set url, data
        resolve data

module.exports = class API
  constructor: (options) ->
    {@url, @params} = options
    @cache = new Cache options

  get: (params) ->
    get @url, (extend {}, @params, params), @cache
