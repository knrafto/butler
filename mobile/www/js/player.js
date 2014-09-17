angular.module('player', ['butler', 'ionic'])

.config(function($stateProvider) {
  $stateProvider.state('app.player', {
    url: '/player',
    views: {
      menuContent: {
        templateUrl: 'templates/player.html',
        controller: 'PlayerCtrl'
      }
    }
  });
})

.controller('PlayerCtrl', function($scope) {
})

.filter('time', function() {
  return function(input) {
    var seconds = (input / 1000) | 0;
    return Math.floor(seconds / 60) + ':' + ('0' + seconds % 60).slice(-2);
  };
});
