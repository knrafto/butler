angular.module('spotify', ['server', 'ionic'])

.config(function($stateProvider) {
  $stateProvider.state('butler.spotify', {
    url: '/spotify',
    views: {
      menuContent: {
        templateUrl: 'templates/spotify.html',
        controller: 'SpotifyCtrl'
      }
    }
  });
})

.controller('SpotifyCtrl', function($scope, server) {
  $scope.search = {
    query: ''
  };

  $scope.$watch('search.query', function(query) {
    if (query) {
      server.post('spotify.search', [query], {
        track_count: 10,
        album_count: 0,
        artist_count: 0,
        playlist_count: 0
      }).then(function(data) {
        if (data.query === query) {
          $scope.results = data;
        }
      });
    } else {
      $scope.results = {};
    }
  });
});
