angular.module('butler', ['ionic'])
.config(function($stateProvider, $urlRouterProvider) {
  $stateProvider

  .state('app', {
    url: '/app',
    abstract: true,
    templateUrl: 'templates/menu.html',
    controller: 'AppCtrl'
  })

  .state('app.player', {
    url: '/player',
    views: {
      'menuContent' :{
        templateUrl: 'templates/player.html'
      }
    }
  });

  // if none of the above states are matched, use this as the fallback
  $urlRouterProvider.otherwise('/app/player');
})

.controller('AppCtrl', function($scope) {
});
