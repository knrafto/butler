angular.module('mopidy', ['butler'])

.config ['$stateProvider', ($stateProvider) ->
  $stateProvider

  .state 'app.mopidy',
    url: '/mopidy'
    abstract: true
    template: '<ion-nav-view></ion-nav-view>'

  .state 'app.mopidy.home',
    url: '/home'
    templateUrl: 'mopidy/templates/home.html'

  .state 'app.mopidy.playback',
    url: '/playback'
    templateUrl: 'mopidy/templates/playback.html'
    controller: 'PlaybackCtrl'

  .state 'app.mopidy.search',
    url: '/search'
    templateUrl: 'mopidy/templates/search.html'

  .state 'app.mopidy.playlists',
    url: '/playlists'
    templateUrl: 'mopidy/templates/playlists.html'

  .state 'app.mopidy.playlist',
    url: '/playlist/:uri'
    templateUrl: 'mopidy/templates/playlist.html'
    controller: ['$scope', '$stateParams', 'mopidy',
      ($scope,  $stateParams,  mopidy) ->
        $scope.playlist = mopidy.getPlaylist $stateParams.uri
    ]
]

.service 'playback', ['$interval', 'butler', 'debounce',
 ($interval, butler, debounce) ->
    playback =
      state: 'stopped'
      currentTlTrack: null
      timePosition: 0

    timer = null
    lastUpdate = null

    updateTimer = ->
      $interval.cancel timer
      lastUpdate = _.now()
      if playback.state is 'playing'
        timer = $interval ->
          playback.timePosition += _.now() - lastUpdate
          lastUpdate = _.now()
        , 100

    updateInterval = 100

    setState = debounce updateInterval, (state) ->
      old = playback.state
      playback.state = state
      updateTimer() unless state is old

    setCurrentTlTrack = debounce updateInterval, (track) ->
      playback.currentTlTrack = track

    setTimePosition = debounce updateInterval, (position) ->
      playback.timePosition = position
      updateTimer()

    raise = (err) -> throw err

    fetch = (method, setter) ->
      (butler.call method).then setter, raise

    sync = ->
      fetch 'mopidy.playback.get_state', setState
      fetch 'mopidy.playback.get_current_tl_track', setCurrentTlTrack
      fetch 'mopidy.playback.get_time_position', setTimePosition

    butler.on 'open', sync

    butler.on 'mopidy.playback_state_changed', (data) ->
      setState data.new_state

    butler.on 'mopidy.track_playback_started', (data) ->
      setCurrentTlTrack data.tl_track
      setTimePosition 0

    butler.on 'mopidy.track_playback_paused', (data) ->
      setCurrentTlTrack data.tl_track
      setTimePosition data.time_position

    butler.on 'mopidy.track_playback_resumed', (data) ->
      setCurrentTlTrack data.tl_track
      setTimePosition data.time_position

    butler.on 'mopidy.track_playback_ended', (data) ->
      setCurrentTlTrack null
      setTimePosition 0

    butler.on 'mopidy.seeked', (data) ->
      setTimePosition data.time_position

    save = (method, args...) ->
      (butler.call method, args...).then null, (err) ->
        sync
        raise err

    playback.play = ->
      playback.state = 'playing'
      save 'mopidy.playback.play'

    playback.pause = ->
      playback.state = 'paused'
      save 'mopidy.playback.pause'

    # TODO: tlTrack
    playback.next = -> save 'mopidy.playback.next'
    playback.previous = -> save 'mopidy.playback.previous'

    playback.seek = (position) ->
      playback.timePosition = position
      save 'mopidy.playback.seek', position

    return playback
]

.controller 'PlaybackCtrl', ['$scope', 'playback', ($scope, playback) ->
  $scope.playback = playback
]

.directive 'mopidyPlayButton', ->
  restrict: 'E'
  replace: true
  scope: true
  template: '''
    <button class="button button-icon icon"
      ng-class="playing ? \'ion-ios7-pause\' : \'ion-ios7-play\'"
      ng-click="toggle()">
    </button>
    '''
  controller: ['$scope', ($scope) ->
    $scope.$watch ->
      $scope.playback.state is 'playing'
    , (playing) ->
      $scope.playing = playing

    $scope.toggle = ->
      if $scope.playing
        $scope.playback.pause()
      else
        $scope.playback.play()
  ]

.directive 'mopidyNextButton', ->
  restrict: 'E'
  replace: true
  template: '''
    <button class="button button-icon icon ion-ios7-skipforward"
      ng-click="playback.next()">
    </button>
    '''

.directive 'mopidyPreviousButton', ->
  restrict: 'E'
  replace: true
  template: '''
    <button class="button button-icon icon ion-ios7-skipbackward"
      ng-click="playback.previous()">
    </button>
    '''

.directive 'mopidySeekSlider', ->
  restrict: 'E'
  replace: true
  scope: true
  template: '''
    <div class="range">
      <i>{{slider.position | time}}</i>
      <input integer type="range"
        min="0" max="{{slider.length}}"
        ng-model="slider.position"
        ng-mousedown="startSeek()"
        ng-mouseup="endSeek()">
      <i>{{slider.length | time}}</i>
    </div>
    '''
  controller: ['$scope', ($scope) ->
    seeking = false

    $scope.slider =
      position: 0
      length: 0

    $scope.$watch ->
      $scope.playback.timePosition
    , (position) ->
      $scope.slider.position = position unless seeking

    $scope.$watch ->
      $scope.playback.currentTlTrack?.track.length
    , (length) ->
      $scope.slider.length = length or 0

    $scope.startSeek = -> seeking = true

    $scope.endSeek = ->
      seeking = false
      $scope.playback.seek $scope.slider.position
  ]

.directive 'mopidyAlbumImage', ->
  restrict: 'E'
  replace: true
  scope:
    album: '='
    size: '@'
  template: '<img></img>'
  controller: ['$scope', '$q', 'butler', ($scope, $q, butler) ->
    @getAlbumImage = ->
      album = $scope.album
      return $q.reject() unless album
      butler.call 'lastfm.albumInfo', album.name, album.artists[0].name
      .then (data) ->
        for image in data.album?.image
          if image.size is $scope.size
            return image['#text']

    return
  ]
  link: (scope, element, attr, ctrl) ->
    scope.$watch 'album.uri', ->
      attr.$set 'src', ''
      ctrl.getAlbumImage().then (image) ->
        attr.$set 'src', image

.directive 'mopidyTrackInfo', ->
  restrict: 'E'
  replace: true
  scope:
    track: '='
  template: '''
    <div>
      <h2>{{track.name}}</h2>
      <p>{{track.artists | pluck:"name" | join:", "}}</p>
    </div>
    '''

# .directive('mopidyTrackList', function() {
#   return {
#     restrict: 'E',
#     replace: true,
#     scope: {
#       tracks: '='
#     },
#     templateUrl: 'templates/mopidy/track-list.html',
#     controller: 'TrackListCtrl'
#   }
# })

# .controller('TrackListCtrl', function($scope, $ionicActionSheet, mopidy) {
#   $scope.trackAction = function(track) {
#     $ionicActionSheet.show({
#       buttons: [
#         { text: 'Queue' },
#         { text: 'Play from here' }
#       ],
#       cancelText: 'Cancel',
#       buttonClicked: function(index) {
#         if (index === 0) {
#           mopidy.queueTrack(track);
#         } else if (index === 1) {
#           mopidy.setTracklist($scope.tracks, track);
#         }
#         return true;
#       }
#     });
#   };
# })

.directive 'mopidyPlaybackBar', ->
  restrict: 'E'
  replace: true
  scope: false
  templateUrl: 'mopidy/templates/playback-bar.html'
  controller: 'PlaybackCtrl'

.directive 'integer', ->
  restrict: 'A'
  require: 'ngModel'
  link: (scope, elm, attrs, ctrl) ->
    ctrl.$parsers.unshift parseInt

.directive 'stopEvent', ->
  restrict: 'A'
  scope:
    name: '@stopEvent'
  link: (scope, element, attr) ->
    element.bind scope.name, (event) ->
      event.stopPropagation()
      event.preventDefault()

.filter 'time', ->
  (input) ->
    seconds = (input / 1000) | 0
    "#{seconds // 60 }:#{('0' + seconds % 60).slice -2}"

.filter 'pluck', -> _.pluck

.filter 'join', ->
  (input, delimeter) -> (input or []).join delimeter or ' '
