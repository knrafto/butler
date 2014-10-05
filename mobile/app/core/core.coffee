angular.module 'core', ['ionic', 'templates', 'butler', 'settings']

.config ['$provide', ($provide) ->
  $provide.decorator '$exceptionHandler', ['$delegate', '$injector',
    ($delegate, $injector) ->
      (err, cause) ->
        ($injector.get 'butler').emit 'error', err, cause
        $delegate err, cause
  ]
]

.run ['$rootScope', '$exceptionHandler', ($rootScope, $exceptionHandler) ->
  $rootScope.$on '$stateChangeError',
    (event, toState, toParams, fromState, fromParams, error) ->
      $exceptionHandler error
]

.factory 'settings', ['$window', ($window) ->
  localStorage = $window.localStorage
  watchers = {}

  watch: (key, fn) ->
    watchers[key] ?= []
    watchers[key].push fn
    value = localStorage.getItem key
    fn value, value
    return

  get: (key) ->
    localStorage.getItem key

  set: (key, value) ->
    old = localStorage.getItem key
    return if value is old
    localStorage.setItem key, value
    for fn in watchers[key] or []
      fn value, old
    return
]

.factory 'debounce', ['$rootScope', ($rootScope) ->
  (wait, fn) ->
    _.debounce (args...) ->
      context = this
      $rootScope.$apply -> fn.apply context, args
    , wait
]
