angular.module('player', ['poll', 'server'])

.controller('PlayerCtrl', function($scope, poll, SERVER_URL) {
  angular.extend($scope, {
    counter: null,
    playing: false,
    position: 0,
    current_track: null,
    queue: [],
    history: []
  });
  $scope.poller = poll(SERVER_URL + '/player/state', function(data) {
    angular.extend($scope, data);
  });

  $scope.$on('$destroy', function() {
    poll.cancel($scope.poller);
  });
})

.controller('PlaybackCtrl', function($scope, $interval, $http, SERVER_URL) {
  var ms = 100;

  $scope.slider = {
    sliding: false,
    position: $scope.position
  };

  $scope.$watch('counter', function() {
    $scope.slider.position = $scope.position;
  });

  $scope.tick = $interval(function() {
    if ($scope.playing && !$scope.slider.sliding) {
      $scope.slider.position = ($scope.slider.position | 0) + ms;
    }
  }, ms);

  $scope.nextTrack = function() {
    $http.post(SERVER_URL + '/player/next_track');
  };

  $scope.prevTrack = function() {
    $http.post(SERVER_URL + '/player/prev_track');
  };

  $scope.toggle = function() {
    $http.post(SERVER_URL + '/player/play', {pause: $scope.playing});
  };

  $scope.startSlide = function() {
    $scope.slider.sliding = true;
  };

  $scope.endSlide = function() {
    $scope.slider.sliding = false;
    $http.post(SERVER_URL + '/player/seek', {seek: $scope.slider.position});
  };

  $scope.$on('$destroy', function() {
    $interval.cancel($scope.tick);
  });
})

.filter('time', function() {
  return function(input) {
    var seconds = (input / 1000) | 0;
    return Math.floor(seconds / 60) + ':' + ('0' + seconds % 60).slice(-2);
  };
});
