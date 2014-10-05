angular.module('app', ['mopidy'])

.config ['$stateProvider', '$urlRouterProvider',
  ($stateProvider, $urlRouterProvider) ->
    $stateProvider.state 'app',
      abstract: true
      templateUrl: 'menu.html'

    $urlRouterProvider.otherwise '/settings'
]
