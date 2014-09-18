angular.module('lastfm', ['butler', 'server', 'underscore'])

.factory('lastfm', function($http, butler, _) {
  var url = 'http://ws.audioscrobbler.com/2.0/';
  var getKey = butler.call('key.lastfm');

  function call(method, params) {
    return getKey.then(function(apiKey) {
      params = params || {};
      params.method = method;
      params.api_key = apiKey;
      return $http.get(url, { params: params });
    });
  }

  return {
    getTrackImage: function(track) {
      return call('album.getInfo', {
        artist: track.artists[0].name,
        album: track.album.name
      }).then(function(response) {
        return _.last(response.data.album.image)['#text'];
      });
    }
  };
});
