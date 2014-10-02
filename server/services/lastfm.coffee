{LastFmNode} = require 'lastfm'
LRU          = require 'lru-cache'
Q            = require 'q'

butler       = require '../butler'
memoize      = require '../async-memoize'

module.exports = (config) ->
  lastfm = new LastFmNode api_key: config.key
  cache = new LRU max: config.cacheSize

  request = memoize cache, (method, options) ->
    "#{method}:#{JSON.stringify(options)}"
  , (method, options) ->
    deferred = Q.defer()
    response = lastfm.request method, options
    response.on 'success', (data) -> deferred.resolve data
    response.on 'error', (err) -> deferred.reject err
    deferred.promise

  butler.register 'lastfm.albumInfo', (album, artist) ->
    request 'album.getInfo', album: album, artist: artist
