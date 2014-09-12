angular.module('server', [])

.constant('SERVER_URL', 'http://localhost:26532')

.factory('server', function(SERVER_URL, $window, $q) {
  var socket = $window.io(SERVER_URL),
      nextId = 0,
      pendingRequests = {},
      callbacks = {};

  socket.on('response', function(data) {
    var deferred = pendingRequests[data.id];
    if (deferred) {
      deferred.resolve(data.result);
      delete pendingRequests[data.id];
    }
  });

  socket.on('error', function(error_name, error_message) {
    angular.forEach(pendingRequests, function(deferred) {
      deferred.reject(error_name + ': ' + error_message);
    });
    pendingRequests = {};
  });

  socket.on('event', function(data) {
    angular.forEach(callbacks[data.name] || [], function(f) {
      f(data.args, data.kwds);
    });
  });

  return {
    emit: function(name, args, kwds) {
      socket.emit('event', {
        name: name,
        args: args || [],
        kwds: kwds || {}
      });
    },

    request: function(method, args, kwds) {
      var requestId = nextId++,
          deferred = $q.defer();
      socket.emit('request', {
        id: requestId,
        method: method,
        args: args || [],
        kwds: kwds || {}
      });
      pendingRequests[requestId] = deferred;
      return deferred.promise;
    },

    on: function(name, f) {
      if (callbacks[name] === undefined) {
        socket.emit('subscribe', {
          name: name
        });
        callbacks[name] = [];
      }
      callbacks[name].push(f);
    },

    off: function(name, f) {
      if (!callbacks[name]) return;
      var i = callbacks[name].indexOf(f);
      if (i != -1) callbacks[name].splice(i, 1);
    }
  };
});
