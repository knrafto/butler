angular.module('player', ['server', 'ionic'])

.config(function($stateProvider) {
  $stateProvider.state('butler.player', {
    url: '/player',
    views: {
      menuContent: {
        templateUrl: 'templates/player.html',
        controller: 'PlayerCtrl'
      }
    },
    resolve: {
      state: function(server) {
        return server.post('player.state');
      }
    }
  });
})

.controller('PlayerCtrl', function($scope, server, state) {
  $scope.state = state;

  function poller(args, kwds) {
    $scope.state = kwds;
  }

  server.on('player.state', poller);

  $scope.$on('$destroy', function() {
    server.off('player.state', poller);
  });
})

.controller('PlaybackCtrl', function($scope, server) {
  $scope.nextTrack = function() {
    server.post('player.next_track');
  };

  $scope.prevTrack = function() {
    server.post('player.prev_track');
  };

  $scope.toggle = function() {
    server.post('player.play', [!$scope.state.playing]);
  };
})

.filter('time', function() {
  return function(input) {
    var seconds = (input / 1000) | 0;
    return Math.floor(seconds / 60) + ':' + ('0' + seconds % 60).slice(-2);
  };
});
