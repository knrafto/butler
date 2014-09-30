var API = require('../api');
var butler = require('../butler');

/** @module lastfm */
module.exports = function(config) {
  var api = new API({
    url: 'http://ws.audioscrobbler.com/2.0/',
    params: {
      api_key: config.key,
      format: 'json'
    },
    max: config.cacheSize || 1000
  });

  butler.register('lastfm.albumInfo', function(album, artist) {
    return api.get({
      method: 'album.getinfo',
      album: album,
      artist: artist
    });
  });
};
