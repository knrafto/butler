angular.module('butler', ['ui.router', 'templates'])

# TODO
.constant 'SERVER_URL', 'ws://localhost:26532'

.factory 'butler', ['$window', '$rootScope', '$timeout', '$q', 'SERVER_URL',
  ($window,  $rootScope,  $timeout,  $q,  SERVER_URL) ->
    butler = new $window.common.Butler()
    client = new $window.common.Client()

    reconnectTimeout = null

    reconnect = ->
      $timeout.cancel reconnectTimeout
      reconnectTimeout = $timeout ->
        client.open SERVER_URL
      , 8000

    client.open SERVER_URL

    client.on 'open', ->
      $timeout.cancel reconnectTimeout
      butler.emit 'open'

    client.on 'close', (code, reason) ->
      butler.emit 'close', code, reason
      reconnect()

    client.on 'error', (errno) ->
      butler.emit 'error', errno
      reconnect()

    client.on 'event', (name, event) ->
      $rootScope.$apply ->
        butler.emit name, event.params...

    butler.register '', (args...) ->
      try
        deferred = $q.defer()
        client.request @name, args, (err, result) ->
          $rootScope.$apply ->
            if err then deferred.reject(err) else deferred.resolve(result)
        return deferred.promise;
      catch err
        $q.reject err

    butler.on '', (args...) ->
      console.log _.now(), @name, args

    return butler
]

.factory 'debounce', ['$rootScope', ($rootScope) ->
  (wait, fn) ->
    _.debounce (args...) ->
      context = this
      $rootScope.$apply -> fn.apply context, args
    , wait
]
