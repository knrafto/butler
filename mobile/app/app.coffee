angular.module('app', ['mopidy', 'settings'])

.config ['$stateProvider', '$urlRouterProvider',
  ($stateProvider, $urlRouterProvider) ->
    $stateProvider

    .state 'app',
      abstract: true
      templateUrl: 'menu.html'

    .state 'app.home',
      url: '/'
      templateUrl: 'home.html'

    $urlRouterProvider.otherwise '/'
]
