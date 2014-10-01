angular.module('mopidy', ['butler'])

.config(function($stateProvider) {
  $stateProvider

  .state('app.mopidy', {
    url: '/mopidy',
    abstract: true,
    template:
      '<ion-nav-view></ion-nav-view>'
  })

  .state('app.mopidy.home', {
    url: '/home',
    templateUrl: 'mopidy/home.html'
  })

  .state('app.mopidy.playback', {
    url: '/playback',
    templateUrl: 'mopidy/playback.html',
    controller: 'PlaybackCtrl'
  })

  .state('app.mopidy.search', {
    url: '/search',
    templateUrl: 'mopidy/search.html'
  })

  .state('app.mopidy.playlists', {
    url: '/playlists',
    templateUrl: 'mopidy/playlists.html'
  })

  .state('app.mopidy.playlist', {
    url: '/playlist/:uri',
    templateUrl: 'mopidy/playlist.html',
    controller: function($scope, $stateParams, mopidy) {
      $scope.playlist = mopidy.getPlaylist($stateParams.uri);
    }
  });
})

.service('playback', function($interval, butler, debounce) {
  var playback = {
    state: 'stopped',
    currentTlTrack: null,
    timePosition: 0
  };

  var timer;
  var lastUpdate;

  function updateTimer() {
    $interval.cancel(timer);
    lastUpdate = Date.now();
    if (playback.state === 'playing') {
      timer = $interval(function() {
        var now = Date.now();
        playback.timePosition += now - lastUpdate;
        lastUpdate = now;
      }, 100);
    }
  }

  var updateInterval = 100;

  var setState = debounce(function(state) {
    var old = playback.state;
    playback.state = state;
    if (state !== old) updateTimer();
  }, updateInterval);

  var setCurrentTlTrack = debounce(function(track) {
    playback.currentTlTrack = track;
  }, updateInterval);

  var setTimePosition = debounce(function(position) {
    playback.timePosition = position;
    updateTimer();
  }, updateInterval);

  function fetch(method, setter) {
    butler.call(method).then(setter);
  }

  function sync() {
    fetch('mopidy.playback.get_state', setState);
    fetch('mopidy.playback.get_current_tl_track', setCurrentTlTrack);
    fetch('mopidy.playback.get_time_position', setTimePosition);
  }

  butler.on('open', sync);

  butler.on('mopidy.playback_state_changed', function(data) {
    setState(data.new_state);
  });

  butler.on('mopidy.track_playback_started', function(data) {
    setCurrentTlTrack(data.tl_track);
    setTimePosition(0);
  });

  butler.on('mopidy.track_playback_paused', function(data) {
    setCurrentTlTrack(data.tl_track);
    setTimePosition(data.time_position);
  });

  butler.on('mopidy.track_playback_resumed', function(data) {
    setCurrentTlTrack(data.tl_track);
    setTimePosition(data.time_position);
  });

  butler.on('mopidy.track_playback_ended', function(data) {
    setCurrentTlTrack(null);
    setTimePosition(0);
  });

  butler.on('mopidy.seeked', function(data) {
    setTimePosition(data.time_position);
  });

  function save(method) {
    var args = _.toArray(arguments).slice(1);
    butler.apply(method, args).then(undefined, sync);
  }

  playback.play = function() {
    playback.state === 'playing';
    save('mopidy.playback.play');
  };

  playback.pause = function() {
    playback.state === 'paused';
    save('mopidy.playback.pause');
  };

  playback.next = function() {
    // TODO: tlTrack
    save('mopidy.playback.next');
  };

  playback.previous = function() {
    // TODO: tlTrack
    save('mopidy.playback.previous');
  };

  playback.seek = function(position) {
    playback.timePosition = position;
    save('mopidy.playback.seek', position);
  };

  return playback;
})

.controller('PlaybackCtrl', function($scope, playback) {
  $scope.playback = playback;
})

.directive('mopidyPlayButton', function() {
  return {
    restrict: 'E',
    replace: true,
    scope: true,
    template:
      '<button class="button button-icon icon"' +
      '  ng-class="playing ? \'ion-ios7-pause\' : \'ion-ios7-play\'"' +
      '  ng-click="toggle()"></button>',
    controller: function($scope) {
      $scope.$watch('playback.state === \'playing\'', function(playing) {
        $scope.playing = playing;
      });

      $scope.toggle = function() {
        $scope.playing ? $scope.playback.pause() : $scope.playback.play();
      };
    }
  }
})

.directive('mopidyNextButton', function() {
  return {
    restrict: 'E',
    replace: true,
    template:
      '<button class="button button-icon icon ion-ios7-skipforward"' +
      '  ng-click="playback.next()"></button>'
  };
})

.directive('mopidyPreviousButton', function() {
  return {
    restrict: 'E',
    replace: true,
    template:
      '<button class="button button-icon icon ion-ios7-skipbackward"' +
      '  ng-click="playback.previous()"></button>'
  };
})

.directive('mopidySeekSlider', function() {
  return {
    restrict: 'E',
    replace: true,
    scope: true,
    template:
      '<div class="range">' +
      '  <i>{{slider.position | time}}</i>' +
      '  <input integer type="range"' +
      '    min="0" max="{{slider.length}}"' +
      '    ng-model="slider.position"' +
      '    ng-mousedown="startSeek()"' +
      '    ng-mouseup="endSeek()">' +
      '  <i>{{slider.length | time}}</i>' +
      '</div>',
    controller: function($scope) {
      var seeking = false;

      $scope.slider = {
        position: 0,
        length: 0
      };

      $scope.$watch('playback.timePosition', function(position) {
        if (!seeking) {
          $scope.slider.position = position;
        }
      });

      $scope.$watch('playback.currentTlTrack.track.length', function(length) {
        $scope.slider.length = length || 0;
      });

      $scope.startSeek = function() {
        seeking = true;
      };

      $scope.endSeek = function() {
        seeking = false;
        $scope.playback.seek($scope.slider.position);
      };
    }
  };
})

.directive('mopidyAlbumImage', function() {
  return {
    restrict: 'E',
    replace: true,
    scope: {
      album: '=',
      size: '@'
    },
    template: '<img></img>',
    controller: function($scope, $q, butler) {
      this.getAlbumImage = function() {
        var album = $scope.album;
        if (!album) return $q.reject();
        return butler.call(
          'lastfm.albumInfo', album.name, album.artists[0].name
        ).then(function(data) {
          var image = _.find(data.album.image,
            _.matches({ size: $scope.size }));
          console.log(image);
          return image && image['#text'];
        });
      };
    },
    link: function(scope, element, attr, ctrl) {
      scope.$watch('album.uri', function() {
        attr.$set('src', '');
        ctrl.getAlbumImage().then(function(image) {
          attr.$set('src', image);
        });
      });
    }
  };
})

.directive('mopidyTrackInfo', function() {
  return {
    restrict: 'E',
    replace: true,
    scope: {
      track: '='
    },
    template:
      '<div>' +
      '  <h2>{{track.name}}</h2>' +
      '  <p>{{track.artists | pluck:"name" | join:", "}}</p>' +
      '</div>'
  };
})

.directive('mopidyTrackList', function() {
  return {
    restrict: 'E',
    replace: true,
    scope: {
      tracks: '='
    },
    templateUrl: 'templates/mopidy/track-list.html',
    controller: 'TrackListCtrl'
  }
})

.controller('TrackListCtrl', function($scope, $ionicActionSheet, mopidy) {
  $scope.trackAction = function(track) {
    $ionicActionSheet.show({
      buttons: [
        { text: 'Queue' },
        { text: 'Play from here' }
      ],
      cancelText: 'Cancel',
      buttonClicked: function(index) {
        if (index === 0) {
          mopidy.queueTrack(track);
        } else if (index === 1) {
          mopidy.setTracklist($scope.tracks, track);
        }
        return true;
      }
    });
  };
})

.directive('mopidyPlaybackBar', function() {
  return {
    restrict: 'E',
    replace: true,
    scope: false,
    templateUrl: 'mopidy/playback-bar.html',
    controller: 'PlaybackCtrl'
  }
})

.directive('integer', function() {
  return {
    restrict: 'A',
    require: 'ngModel',
    link: function(scope, elm, attrs, ctrl) {
      ctrl.$parsers.unshift(parseInt);
    }
  };
})

.directive('stopEvent', function() {
  return {
    restrict: 'A',
    scope: {
      name: '@stopEvent'
    },
    link: function(scope, element, attr) {
      element.bind(scope.name, function(event) {
        event.stopPropagation();
        event.preventDefault();
      });
    }
  };
})

.filter('time', function() {
  return function(input) {
    var seconds = (input / 1000) | 0;
    return Math.floor(seconds / 60) + ':' + ('0' + seconds % 60).slice(-2);
  };
})

.filter('pluck', function() {
  return _.pluck;
})

.filter('join', function() {
  return function(input, delimeter) {
    return (input || []).join(delimeter || ' ');
  };
});
