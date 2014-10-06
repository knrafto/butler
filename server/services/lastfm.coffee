API    = require '../api'
butler = require '../butler'

module.exports = (config) ->
  lastfm = new API
    url: 'http://ws.audioscrobbler.com/2.0/'
    params:
      api_key: config.key
      format: 'json'
    max: config.cacheSize

  butler.register 'lastfm', (params) ->
    params.method = @suffix
    lastfm.get params
