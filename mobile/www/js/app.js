angular.module('app', ['mopidy', 'ionic'])

.config(function($stateProvider, $urlRouterProvider) {
  $stateProvider.state('app', {
    abstract: true,
    templateUrl: 'templates/menu.html',
  });

  $urlRouterProvider.otherwise('/mopidy/home');
});
