angular.module('app', ['mopidy', 'ionic'])

.config(function($stateProvider) {
  $stateProvider.state('app', {
    abstract: true,
    templateUrl: 'templates/menu.html',
  });
});
