angular.module('app', ['mopidy', 'templates', 'ionic'])

.config(function($stateProvider, $urlRouterProvider) {
  $stateProvider.state('app', {
    abstract: true,
    templateUrl: 'menu.html',
  });

  $urlRouterProvider.otherwise('/mopidy/home');
});
