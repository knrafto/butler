angular.module('butler', ['underscore'])

.constant('SERVER_URL', 'http://localhost:26532')

.factory('socket', function($window, SERVER_URL) {
  return $window.io(SERVER_URL);
})

.factory('butler', function(socket, $q, _) {
  var nextId = 0;
  var pendingRequests = {};
  var _events = {};

  function walk(name) {
    var prefix = [];
    var prefixes = [''];
    _.each(name.split('.'), function(namePart) {
      prefix.push(namePart);
      prefixes.push(prefix.join('.'));
    });
    return prefixes;
  }

  function resolve(response) {
    var deferred = pendingRequests[response.id];
    if (deferred) {
      if (response.result) {
        deferred.resolve(response.result);
      } else {
        deferred.reject(response.error || 'unknown error');
      }
      delete pendingRequests[response.id];
    }
  }

  function emit(name, args) {
    var context = { event: name };
    var fns = _.chain(walk(name))
      .map(function(prefix) { return _events[prefix]; })
      .compact()
      .flatten()
      .value();
    _.each(_.toArray(fns), function(fn) {
      fn.apply(context, args);
    });
  }

  var butler = {
    on: function(name, fn) {
      if (!fn) {
        fn = name;
        name = '';
      }
      var events = _events[name] || (_events[name] = []);
      events.push(fn);
      return butler;
    },

    off: function(name, fn) {
      if (!fn) {
        fn = name;
        name = '';
      }
      var events = _events[name];
      if (events) {
        var i = events.indexOf(fn);
        if (i > -1) events.splice(i, 1);
      }
      return butler;
    },

    call: function(method) {
      var requestId = nextId++;
      var deferred = $q.defer();
      var args = _.toArray(arguments).slice(1);
      socket.emit('request', {
        id: requestId,
        method: method,
        params: args
      });
      pendingRequests[requestId] = deferred;
      return deferred.promise;
    }
  };

  socket.on('response', resolve);

  socket.on('event', function(event) {
    console.log(event);
    emit(event.event, event.params);
  });

  return butler;
});
