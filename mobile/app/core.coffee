angular.module('core', ['ionic', 'templates'])

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

.factory 'butler', ['$window', ($window) ->
  {Butler} = $window.common
  new Butler
]

.run ['$window', '$exceptionHandler', '$rootScope', '$q', 'butler', 'settings'
  ($window, $exceptionHandler, $rootScope, $q, butler, settings) ->
    {Action, Client} = $window.common
    client = null

    emit = (name, args...) ->
      $rootScope.$apply ->
        butler.emit name, args...

    connect = new Action (url) ->
      client?.close()
      client = null

      try
        client = new Client url
      catch err
        $exceptionHandler err
        return

      client.on 'open', ->
        emit 'open'

      client.on 'close', (code, reason) ->
        emit 'close', code, reason
        connect.run 2000, url

      client.on 'error', (err) ->
        $exceptionHandler err
        connect.run 2000, url

      client.on 'event', (name, event) ->
        emit name, event.params...

    settings.watch 'butler.url', (url) ->
      connect.run 0, url

    butler.on '', (args...) ->
      console.log @name, args...

    butler.register '', (args...) ->
      method = @name
      $q (resolve, reject) ->
        args = (angular.copy arg for arg in args)
        client.request method, args, (err, result) ->
          console.log method, args..., err or result
          if err? then reject err else resolve result
]

.run ['$rootScope', '$exceptionHandler', ($rootScope, $exceptionHandler) ->
  $rootScope.$on '$stateChangeError',
    (event, toState, toParams, fromState, fromParams, error) ->
      $exceptionHandler error
]
