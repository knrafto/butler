angular.module('server', [])

.factory('EventEmitter', function() {
  function EventEmitter(obj) {
    if (obj) {
      angular.forEach(EventEmitter.prototype, function(value, key) {
        obj[key] = value;
      });
      return obj;
    }
  }

  EventEmitter.prototype = {
    on: function(event, fn) {
      this._callbacks = this._callbacks || {};
      (this._callbacks[event] = this._callbacks[event] || []).push(fn);
      return this;
    },

    off: function(event, fn) {
      this._callbacks = this._callbacks || {};
      var callbacks = this._callbacks[event];
      if (!callbacks) return this;
      var i = callbacks.indexOf(fn);
      if (i > -1) callbacks.splice(i, 1);
      return this;
    },

    emit: function(event) {
      this._callbacks = this._callbacks || {};
      var args = Array.prototype.slice.call(arguments, 1),
          callbacks = this._callbacks[event];

      if (callbacks) {
        callbacks = callbacks.slice(0);
        angular.forEach(callbacks, function(fn) {
          fn.apply(this, args);
        });
      }

      return this;
    },

    listeners: function(event) {
      this._callbacks = this._callbacks || {};
      return this._callbacks[event] || [];
    },

    hasListeners: function(event) {
      return !! this.listeners(event).length;
    }
  };

  return EventEmitter;
})

.factory('server', function(EventEmitter, $window, $q) {
  return function(url) {
    var socket = $window.io.connect(url),
        nextId = 0,
        pendingRequests = {},
        subscribed = {};

    var server = {
      send: function(name, args, kwds) {
        socket.emit('event', {
          name: name,
          args: args || [],
          kwds: kwds || {}
        });
      },

      post: function(method, args, kwds) {
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
      }
    };

    EventEmitter(server);

    var on = server.on;
    server.on = function(event, fn) {
      if (!subscribed[event]) {
        socket.emit('subscribe', {
          name: event
        });
        subscribed[event] = true;
      }
      on.call(this, event, fn);
    };

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
      server.emit(data.name, data.args, data.kwds);
    });

    return server;
  };
});
