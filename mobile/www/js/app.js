angular.module('butler', ['ionic', 'poll'])

.constant('SERVER_URL', 'http://127.0.0.1:26532')

.config(function($stateProvider, $urlRouterProvider) {
  $stateProvider

  .state('app', {
    url: '/app',
    abstract: true,
    templateUrl: 'templates/menu.html',
  })

  .state('app.player', {
    url: '/player',
    views: {
      'menuContent': {
        templateUrl: 'templates/player.html',
        controller: 'PlayerCtrl'
      }
    }
  });

  // if none of the above states are matched, use this as the fallback
  $urlRouterProvider.otherwise('/app/player');
})

.filter('time', function() {
  return function(input) {
    var seconds = (input / 1000) | 0;
    return Math.floor(seconds / 60) + ':' + ('0' + seconds % 60).slice(-2);
  };
})

.controller('PlayerCtrl', function($scope, $http, $interval, poll, SERVER_URL) {
  angular.extend($scope, {
    playing: false,
    position: 0,
    current_track: null,
    queue: [],
    history: []
  });
  $scope.slider = {};
  $scope.slider.position = $scope.position;

  poll(SERVER_URL + '/player/state', function(data) {
    angular.extend($scope, data);
    $scope.slider.position = $scope.position;
  });

  $scope.stopTick = $interval(function() {
    if ($scope.playing && !$scope.slider.sliding) {
      $scope.slider.position = +$scope.slider.position + 100;
    }
  }, 100);

  $scope.nextTrack = function() {
    $http.post(SERVER_URL + '/player/next_track');
  };

  $scope.prevTrack = function() {
    $http.post(SERVER_URL + '/player/prev_track');
  };

  $scope.toggle = function() {
    $http.post(SERVER_URL + '/player/play', {pause: $scope.playing});
  };

  $scope.slider.touch = function() {
    $scope.slider.sliding = true;
  };

  $scope.slider.release = function() {
    $scope.slider.sliding = false;
    $http.post(SERVER_URL + '/player/seek', {seek: $scope.slider.position});
  };

  $scope.$on('destroy', function() {
    $interval.cancel($scope.stopTick);
  });

});

angular.module('poll', [])
.factory('poll', function($http, $log, $timeout) {
  return function(url, callback) {
    var counter = null;

    (function loop() {
      params = {};
      if (counter != null) {
        params.counter = counter;
      }

      $http({
        method: 'GET',
        url: url,
        params: params
      })
      .success(function(data, status, headers, config) {
        var i;
        counter = data.counter;
        callback(data);
        $timeout(loop, 0);
      })
      .error(function(data, status, headers, config) {
        counter = null;
        $timeout(loop, 5000);
      })
    }());
  };
});
