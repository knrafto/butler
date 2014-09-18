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

  _.each('play pause previous next'.split(' '), function(method) {
    mopidy[method] = function() {
      return butler.call('mopidy.playback.' + method);
    };
  });

  mopidy.seek = function(position) {
    return butler.call('mopidy.playback.seek', { time_position: position });
  }

  _.each('setRandom setRepeat setSingle'.split(' '), function(method) {
    mopidy[method] = function(value) {
      return butler.call('mopidy.tracklist.' + method, { value: value });
    };
  });

  var syncMethods = {
    currentTlTrack: 'mopidy.playback.getCurrentTlTrack',
    random: 'mopidy.tracklist.getRandom',
    repeat: 'mopidy.tracklist.getRepeat',
    single: 'mopidy.tracklist.getSingle',
    state: 'mopidy.playback.getState',
    timePosition: 'mopidy.playback.getTimePosition',
    tracklist: 'mopidy.tracklist.getTlTracks'
  };

  function sync(properties) {
    properties = properties || _.keys(syncMethods);
    _.each(properties, function(property) {
      butler.call(syncMethods[property]).then(function(data) {
        mopidy[property] = data;
        startTimer();
      });
    });
  }

  butler.on('mopidy.playbackStateChanged', function(data) {
    mopidy.state = data.new_state;
    startTimer();
  });

  butler.on('mopidy.trackPlaybackStarted', function(data) {
    mopidy.currentTlTrack = data.tl_track;
    mopidy.timePosition = 0;
    startTimer();
  });

  butler.on('mopidy.trackPlaybackPaused', function(data) {
    mopidy.currentTlTrack = data.tl_track;
    mopidy.timePosition = data.time_position;
    startTimer();
  });

  butler.on('mopidy.seeked', function(data) {
    mopidy.timePosition = data.time_position;
    startTimer();
  });

  butler.on('mopidy.tracklistChanged', function(data) {
    mopidy.sync(['tracklist']);
  });

  butler.on('mopidy.optionsChanged', function(data) {
    mopidy.sync(['random', 'repeat', 'single']);
  });

  sync();

  return mopidy;
})

.controller('PlaybackCtrl', function($scope, mopidy, lastfm, _) {
  var seeking = false;
  $scope.slider = {};

  $scope.$watch(function() {
    return mopidy.state;
  }, function(state) {
    $scope.playing = state === 'playing';
  });

  $scope.$watch(function() {
    return mopidy.currentTlTrack && mopidy.currentTlTrack.track.uri;
  }, function() {
    $scope.trackLength = mopidy.currentTlTrack ?
      mopidy.currentTlTrack.track.length : 0;
  })

  $scope.$watch(function() {
    return mopidy.timePosition;
  }, function(position) {
    if (!seeking) {
      $scope.slider.position = position;
    }
  });

  _.each(['random', 'repeat'], function(property) {
    $scope.$watch(function() {
      return mopidy[property];
    }, function(value) {
      $scope[property] = value;
    });
  });

  $scope.next = function() {
    mopidy.next();
  };

  $scope.previous = function() {
    mopidy.previous();
  };

  $scope.toggleState = function() {
    $scope.playing ? mopidy.pause() : mopidy.play();
  };

  $scope.toggleRepeat = function() {
    mopidy.setRepeat(!$scope.repeat);
  };

  $scope.toggleRandom = function() {
    mopidy.setRandom(!$scope.random);
  };

  $scope.startSeek = function() {
    seeking = true;
  };

  $scope.endSeek = function() {
    seeking = false;
    mopidy.seek($scope.slider.position);
  };
})

.directive('integer', function() {
  return {
    require: 'ngModel',
    link: function(scope, elm, attrs, ctrl) {
      ctrl.$parsers.unshift(parseInt);
    }
  };
})

.filter('time', function() {
  return function(input) {
    var seconds = (input / 1000) | 0;
    return Math.floor(seconds / 60) + ':' + ('0' + seconds % 60).slice(-2);
  };
});
