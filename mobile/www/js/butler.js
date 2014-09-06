angular.module('butler', ['ionic', 'player'])

.config(function($stateProvider, $urlRouterProvider) {
  $stateProvider

  .state('butler', {
    url: '/app',
    abstract: true,
    templateUrl: 'templates/menu.html',
  })

  .state('butler.player', {
    url: '/player',
    views: {
      'menuContent': {
        templateUrl: 'templates/player.html',
        controller: 'PlayerCtrl'
      }
    }
  });

  // if none of the above states are matched, use this as the fallback
  $urlRouterProvider.otherwise('/butler/player');
});
