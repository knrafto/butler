angular.module('butler', ['ionic'])

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
      'menuContent' :{
        templateUrl: 'templates/player.html'
      }
    },
    controller: 'PlayerCtrl'
  });

  // if none of the above states are matched, use this as the fallback
  $urlRouterProvider.otherwise('/app/player');
})

.controller('PlayerCtrl', function($scope) {
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
        $log.warn('Error retrieving data from ' + config.url);
        $timeout(loop, 5000);
      })
    }());
  };
});
