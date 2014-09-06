angular.module('poll', [])
.factory('poll', function($q, $timeout, $http) {
  function poll(url, callback) {
    var counter = null,
        deferred = $q.defer(),
        promise = deferred.promise,
        timeout;

    function loop() {
      $http({
        method: 'GET',
        url: url,
        params: counter == null ? {} : {counter: counter},
        timeout: promise
      })
      .success(function(data) {
        counter = data.counter;
        callback(data);
        timeout = $timeout(loop, 1);
      })
      .error(function() {
        counter = null;
        timeout = $timeout(loop, 5000);
      });
    }

    timeout = $timeout(loop, 1);

    promise.then(function() {
      if (timeout) {
        cancelled = $timeout.cancel(timeout);
      }
    });

    return {
      cancel: function() {
        deferred.resolve();
      }
    };
  }

  poll.cancel = function(poller) {
    poller.cancel();
  };

  return poll;
});
