angular.module('lastfm', ['server', 'underscore'])

.factory('lastfm', function($http, butler, _) {
  var url = 'http://ws.audioscrobbler.com/2.0/';
  var getKey = butler.call('key.lastfm');

  function call(method, params) {
    return getKey.then(function(apiKey) {
      params = _.extend(params, {
        api_key: apiKey,
        format: 'json',
        method: method
      });
      return $http.get(url, { params: params });
    });
  }

  return {
    // TODO: cache
    getAlbumImage: function(album, size) {
      return call('album.getInfo', {
        artist: album.artists[0].name,
        album: album.name
      }).then(function(response) {
        var image = _.find(response.data.album.image,
          _.matches({ size: size }));
        return image && image['#text'];
      });
    }
  };
});
