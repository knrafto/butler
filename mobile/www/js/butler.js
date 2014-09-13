angular.module('butler', ['ionic', 'player'])

.config(function($stateProvider) {
  $stateProvider.state('butler', {
    url: '/butler',
    abstract: true,
    templateUrl: 'templates/menu.html',
  });
});
