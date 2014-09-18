angular.module('server', ['butler', 'underscore'])

.constant('SERVER_URL', 'http://127.0.0.1:26532')

.factory('socket', function($window, SERVER_URL) {
  var io = $window.io || angular.noop;
  return io(SERVER_URL);
})

.run(function($rootScope, $exceptionHandler, $q, socket, butler, _) {
  if (!socket) return;

  var nextId = 0;
  var pendingRequests = {};

  butler.register(function() {
    var requestId = nextId++;
    var deferred = $q.defer();
    var request = {
        id: requestId,
        method: this.method,
        params: _.toArray(arguments)
    };
    try {
      socket.emit('request', request);
    } catch (e) {
      $exceptionHandler(e);
    }
    pendingRequests[requestId] = deferred;
    return deferred.promise;
  });

  socket.on('response', function(response) {
    $rootScope.$apply(function() {
      var deferred = pendingRequests[response.id];
      if (deferred) {
        if (response.error) {
          deferred.reject(response.error);
        } else {
          deferred.resolve(response.result);
        }
        delete pendingRequests[response.id];
      }
    });
  });

  socket.on('event', function(event) {
    $rootScope.$apply(function() {
      butler.emit.apply(butler, [event.event].concat(event.params));
    });
  });
});
