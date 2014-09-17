angular.module('app', ['ionic'])

.config(function($stateProvider) {
  $stateProvider.state('app', {
    url: '/app',
    abstract: true,
    templateUrl: 'templates/menu.html',
  });
});
