angular.module('mopidy', ['butler', 'lastfm', 'server', 'ui.router', 'underscore'])

.config(function($stateProvider) {
  $stateProvider.state('app.mopidy', {
    url: '/mopidy',
    views: {
      menuContent: {
        templateUrl: 'templates/mopidy.html'
      }
    }
  });
})

.service('mopidy', function($interval, butler, _) {
  function sync() {
    var properties = {
      currentTlTrack: 'mopidy.playback.getCurrentTlTrack',
      state: 'mopidy.playback.getState',
      timePosition: 'mopidy.playback.getTimePosition',
      tracklist: 'mopidy.tracklist.getTracks'
    };

    _.each(properties, function(method, property) {
      butler.call(method).then(function(data) {
        mopidy[property] = data;
      });
    });
  }

  function call(method) {
    return function(params) {
      return butler.call(method, params);
    };
  }

  var tick;
  var lastUpdate;

  function startTimer() {
    if (tick) $interval.cancel(tick);
    if (mopidy.state === 'playing') {
      lastUpdate = Date.now();
      tick = $interval(function() {
        var now = Date.now();
        mopidy.timePosition += now - lastUpdate;
        lastUpdate = now;
      }, 100);
    }
  }

  var mopidy = {
    sync: sync
  };

  _.each('play pause previous next seek'.split(' '), function(method) {
    mopidy[method] = function(params) {
      return butler.call('mopidy.playback.' + method, params);
    };
  });

  sync();

  butler.on('mopidy.playbackStateChanged', function(data) {
    mopidy.state = data.new_state;
    startTimer();
  });

  butler.on('mopidy.trackPlaybackStarted', function(data) {
    mopidy.currentTlTrack = data.tl_track;
    mopidy.timePosition = 0;
  });

  butler.on('mopidy.trackPlaybackPaused', function(data) {
    mopidy.currentTlTrack = data.tl_track;
    mopidy.timePosition = data.time_position;
  });

  butler.on('mopidy.seeked', function(data) {
    mopidy.timePosition = data.time_position;
  });

  return mopidy;
})

.controller('PlaybackCtrl', function($scope, mopidy, lastfm, _) {
  var seeking = false;
  $scope.slider = {};
  $scope.mopidy = mopidy;

  $scope.$watch('mopidy.timePosition', function() {
    if (!seeking) {
      $scope.slider.position = mopidy.timePosition;
    }
  });

  $scope.next = function() {
    mopidy.next();
  };

  $scope.previous = function() {
    mopidy.previous();
  };

  $scope.toggleState = function() {
    $scope.mopidy.state === 'playing' ? mopidy.pause() : mopidy.play();
  };

  $scope.startSeek = function() {
    seeking = true;
  };

  $scope.endSeek = function() {
    seeking = false;
    mopidy.seek({ time_position: $scope.slider.position });
  };
})

.directive('integer', function() {
  return {
    require: 'ngModel',
    link: function(scope, elm, attrs, ctrl) {
      ctrl.$parsers.unshift(function(viewValue) {
        return parseInt(viewValue);
      });
    }
  };
})

.filter('time', function() {
  return function(input) {
    var seconds = (input / 1000) | 0;
    return Math.floor(seconds / 60) + ':' + ('0' + seconds % 60).slice(-2);
  };
});
