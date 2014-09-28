angular.module('mopidy', ['butler', 'ui.router', 'templates', 'underscore'])

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
    templateUrl: 'mopidy/playback.html'
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

.directive('mopidyShuffleButton', function() {
  return {
    restrict: 'E',
    replace: true,
    template:
      '<button class="button button-icon icon ion-shuffle"' +
      '  ng-click="mopidy.shuffle()"></button>'
  };
})

.directive('mopidySeekSlider', function() {
  return {
    restrict: 'E',
    replace: true,
    scope: true,
    template:
      '<div class="range seek-slider">' +
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
    restrict: 'E',
    replace: true,
    scope: {
      album: '=',
      size: '@'
    },
    template: '<img class="album-image"></img>',
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
    restrict: 'E',
    replace: true,
    scope: {
      track: '='
    },
    template:
      '<div class="track-info"' +
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
