API    = require '../api'
butler = require '../butler'

module.exports = (config) ->
  api = new API
    url: 'http://ws.audioscrobbler.com/2.0/'
    params:
      api_key: config.key
      format: 'json'
    max: config.cacheSize or 1000

  butler.register 'lastfm.albumInfo', (album, artist) ->
    api.get
      method: 'album.getInfo'
      album: album
      artist: artist
