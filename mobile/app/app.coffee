angular.module('app', ['mopidy', 'templates', 'ionic'])

.config ['$stateProvider', '$urlRouterProvider',
  ($stateProvider ,  $urlRouterProvider) ->
    $stateProvider.state 'app',
      abstract: true
      templateUrl: 'menu.html'

    $urlRouterProvider.otherwise '/mopidy/home'
]
