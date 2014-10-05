angular.module('butler', ['settings'])

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
      client = new Client url

      client.on 'open', ->
        emit 'open'

      client.on 'close', (code, reason) ->
        emit 'close', code, reason
        connect.callLater 2000, url

      client.on 'error', (err) ->
        $exceptionHandler err
        connect.callLater 2000, url

      client.on 'event', (name, event) ->
        emit name, event.params...

    settings.watch 'butler.url', (url) ->
      connect.callNow url

    butler.on '', (args...) ->
      console.log @name, args...

    butler.register '', (args...) ->
      method = @name
      $q (resolve, reject) ->
        args = (angular.copy arg for arg in args)
        client.request method, args, (err, result) ->
          if err? then reject err else resolve result
]
