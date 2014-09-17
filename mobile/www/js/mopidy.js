angular.module('mopidy', ['butler', 'ionic'])

.config(function($stateProvider) {
  $stateProvider.state('app.mopidy', {
    url: '/mopidy',
    views: {
      menuContent: {
        templateUrl: 'templates/mopidy.html',
        controller: 'PlaybackCtrl'
      }
    }
    // TODO: resolve
  });
})

.controller('PlaybackCtrl', function($scope, butler) {
  butler.call('mopidy.getState').then(function(state) {
    $scope.newState = state;
  });

  butler.call('mopidy.getCurrentTlTrack').then(function(tlTrack) {
    $scope.currentTlTrack = tlTrack;
  });

  butler.on('mopidy', function(data) {
    _.extend($scope, data);
    console.log($scope);
  });
})

.filter('time', function() {
  return function(input) {
    var seconds = (input / 1000) | 0;
    return Math.floor(seconds / 60) + ':' + ('0' + seconds % 60).slice(-2);
  };
});
