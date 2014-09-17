angular.module('mopidy', ['butler', 'server', 'ui.router', 'underscore'])

.config(function($stateProvider) {
  $stateProvider.state('app.mopidy', {
    url: '/mopidy',
    views: {
      menuContent: {
        templateUrl: 'templates/mopidy.html',
        controller: 'PlaybackCtrl'
      }
    }
    // TODO: resolve
  });
})

.controller('PlaybackCtrl', function($scope, $interval, butler, _) {
  $scope.playback = {};

  var properties = ['currentTrack', 'state', 'timePosition'];
  _.each(properties, function(property) {
    var method = 'mopidy.playback.get' +
      property.charAt(0).toUpperCase() +
      property.slice(1);
    butler.call(method).then(function(data) {
      $scope.playback[property] = data;
    });
  });

  butler.on('mopidy.playbackStateChanged', function(data) {
    $scope.playback.state = data.new_state;
  });

  butler.on('mopidy.trackPlaybackStarted', function(data) {
    $scope.playback.currentTrack = data.tl_track.track;
    $scope.playback.timePosition = 0;
  });

  butler.on('mopidy.trackPlaybackPaused', function(data) {
    $scope.playback.currentTrack = data.tl_track.track;
    $scope.playback.timePosition = data.time_position;
  });

  butler.on('mopidy.seeked', function(data) {
    $scope.playback.timePosition = data.time_position;
  });

  var seeking = false;

  var lastUpdate = Date.now();

  var tick = $interval(function() {
    if ($scope.isPlaying() && !seeking) {
      var now = Date.now();
      $scope.playback.timePosition += now - lastUpdate;
      lastUpdate = now;
    }
  }, 100);

  $scope.isPlaying = function() {
    return $scope.playback.state === 'playing';
  };

  $scope.next = function() {
    butler.call('mopidy.playback.next');
  };

  $scope.previous = function() {
    butler.call('mopidy.playback.previous');
  };

  $scope.toggleState = function() {
    butler.call('mopidy.playback.' +
      ($scope.isPlaying() ? 'pause' : 'play'));
  };

  $scope.startSeek = function() {
    seeking = true;
  };

  $scope.endSeek = function() {
    seeking = false;
    butler.call('mopidy.playback.seek', {
      time_position: $scope.playback.timePosition
    });
  };

  $scope.$on('$destroy', function() {
    $interval.cancel(tick);
  });
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
