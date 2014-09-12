angular.module('player', ['server'])

.controller('PlayerCtrl', function($scope, server) {
  angular.extend($scope, {
    playing: false,
    current_track: null,
    queue: [],
    history: []
  });

  function poller(args, kwds) {
    angular.extend($scope, kwds);
  }

  server.on('player.state', poller);

  $scope.$on('$destroy', function() {
    server.off('player.state', poller);
  });
})

.controller('PlaybackCtrl', function($scope, $interval, server) {
  $scope.nextTrack = function() {
    server.post('player.next_track');
  };

  $scope.prevTrack = function() {
    server.post('player.prev_track');
  };

  $scope.toggle = function() {
    server.post('player.play', [!$scope.playing]);
  };
})

.filter('time', function() {
  return function(input) {
    var seconds = (input / 1000) | 0;
    return Math.floor(seconds / 60) + ':' + ('0' + seconds % 60).slice(-2);
  };
});
