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

.controller('PlayerCtrl', function($scope, $http, poll, SERVER_URL) {
  poll(SERVER_URL + '/player/state', function(data) {
    $scope.playing = data.playing;
    $scope.current_track = data.current_track;
    $scope.queue = data.queue;
    $scope.history = data.history;
  });

  $scope.nextTrack = function() {
    $http.post(SERVER_URL + '/player/next_track');
  };

  $scope.prevTrack = function() {
    $http.post(SERVER_URL + '/player/prev_track');
  };

  $scope.nextSet = function() {
    $http.post(SERVER_URL + '/player/next_set');
  };

  $scope.toggle = function() {
    var pause = $scope.playing;
    $http.post(SERVER_URL + '/player/play', {pause: pause});
  };

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
