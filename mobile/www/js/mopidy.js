angular.module('mopidy', ['butler', 'lastfm', 'server', 'ui.router', 'underscore'])

.config(function($stateProvider) {
  $stateProvider

  .state('app.mopidy', {
    url: '/mopidy',
    abstract: true,
    template:
      '<ion-nav-view></ion-nav-view>',
    controller: function($scope, mopidy) {
      $scope.mopidy = mopidy;
    }
  })

  .state('app.mopidy.home', {
    templateUrl: 'templates/mopidy/home.html'
  })

  .state('app.mopidy.playback', {
    url: '/playback',
    templateUrl: 'templates/mopidy/playback.html'
  })

  .state('app.mopidy.search', {
    url: '/search',
    templateUrl: 'templates/mopidy/search.html'
  })

  .state('app.mopidy.playlists', {
    url: '/playlists',
    templateUrl: 'templates/mopidy/playlists.html'
  })

  .state('app.mopidy.playlist', {
    url: '/playlist/:uri',
    templateUrl: 'templates/mopidy/playlist.html',
    controller: function($scope, playlist) {
      $scope.playlist = playlist;
    },
    resolve: {
      playlist: function($stateParams, mopidy) {
        return mopidy.getPlaylist($stateParams.uri);
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

  mopidy.getPlaylist = function(uri) {
    return butler.call('mopidy.playlists.lookup', { uri: uri });
  };

  var syncMethods = {
    currentTlTrack: 'mopidy.playback.getCurrentTlTrack',
    playlists: 'mopidy.playlists.getPlaylists',
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

  _.each(['mopidy.playlistChanged', 'mopidy.playlistsLoaded'], function(name) {
    butler.on(name, function() {
      mopidy.sync(['playlists']);
    });
  });

  sync();

  return mopidy;
})

.directive('mopidyPlayButton', function() {
  return {
    restrict: 'E',
    replace: true,
    template:
      '<button class="button button-icon icon"' +
      '  ng-class="mopidy.state === \'playing\'' +
      '    ? \'ion-ios7-pause\' : \'ion-ios7-play\'"' +
      '  ng-click="mopidy.state === \'playing\'' +
      '    ? mopidy.pause() : mopidy.play()"></button>'
  };
})

.directive('mopidyNextButton', function() {
  return {
    restrict: 'E',
    replace: true,
    template:
      '<button class="button button-icon icon ion-ios7-skipforward"' +
      '  ng-click="mopidy.next()"></button>'
  };
})

.directive('mopidyPreviousButton', function() {
  return {
    restrict: 'E',
    replace: true,
    template:
      '<button class="button button-icon icon ion-ios7-skipbackward"' +
      '  ng-click="mopidy.previous()"></button>'
  };
})

.directive('mopidyRepeatButton', function() {
  return {
    restrict: 'E',
    replace: true,
    template:
      '<button class="button button-icon icon ion-loop"' +
      '  ng-class="{balanced: mopidy.repeat}"' +
      '  ng-click="mopidy.setRepeat(!mopidy.repeat)"></button>'
  };
})

.directive('mopidyRandomButton', function() {
  return {
    restrict: 'E',
    replace: true,
    template:
      '<button class="button button-icon icon ion-shuffle"' +
      '  ng-class="{balanced: mopidy.random}"' +
      '  ng-click="mopidy.setRandom(!mopidy.random)"></button>'
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
      '    on-touch="startSeek()"' +
      '    on-release="endSeek()">' +
      '  <i>{{slider.length | time}}</i>' +
      '</div>',
    controller: function($scope) {
      var seeking = false;

      $scope.slider = {
        position: 0,
        length: 0
      };

      $scope.$watch('mopidy.timePosition', function(position) {
        if (!seeking) {
          $scope.slider.position = position;
        }
      });

      $scope.$watch('mopidy.currentTlTrack.track.length', function(length) {
        $scope.slider.length = length || 0;
      });

      $scope.startSeek = function() {
        seeking = true;
      };

      $scope.endSeek = function() {
        seeking = false;
        $scope.mopidy.seek($scope.slider.position);
      };
    }
  };
})

.directive('mopidyAlbumImage', function() {
  return {
    restrict: 'A',
    scope: {
      album: '=mopidyAlbumImage',
      size: '@'
    },
    controller: function($scope, $q, lastfm) {
      this.getAlbumImage = function() {
        if (!$scope.album) return $q.reject();
        return lastfm.getAlbumImage($scope.album, $scope.size);
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
    restrict: 'A',
    scope: {
      track: '=mopidyTrackInfo'
    },
    template:
      '<h2>{{track.name}}</h2>' +
      '<p>{{track.artists | pluck:"name" | join:", "}}</p>'
  };
})

.directive('mopidyTrackList', function() {
  return {
    restrict: 'A',
    replace: true,
    scope: {
      tracks: '=mopidyTrackList'
    },
    templateUrl: 'templates/mopidy/track-list.html'
  }
})

.directive('mopidyPlaybackBar', function() {
  return {
    restrict: 'E',
    replace: true,
    scope: false,
    templateUrl: 'templates/mopidy/playback-bar.html'
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

.directive('stopEvent', function () {
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

.filter('pluck', function(_) {
  return function(input, name) {
    return _.pluck(input, name);
  };
})

.filter('join', function() {
  return function(input, delimeter) {
    return (input || []).join(delimeter || ' ');
  };
});
