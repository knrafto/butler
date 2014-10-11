angular.module('mopidy', ['core'])

.config ['$stateProvider', ($stateProvider) ->
  $stateProvider

  .state 'app.mopidy',
    url: '/mopidy'
    abstract: true
    template: '<ion-nav-view></ion-nav-view>'

  .state 'app.mopidy.home',
    url: '/home'
    templateUrl: 'mopidy/templates/home.html'
    controller: ['$scope', 'playlists', ($scope, playlists) ->
      $scope.playlists = playlists
    ]
    resolve:
      playlists: ['mopidy', (mopidy) ->
        mopidy.getPlaylists()
      ]

  .state 'app.mopidy.playback',
    url: '/playback'
    templateUrl: 'mopidy/templates/playback.html'
    controller: 'MopidyCtrl'

  .state 'app.mopidy.search',
    url: '/search'
    templateUrl: 'mopidy/templates/search.html'
    controller: 'SearchCtrl'

  .state 'app.mopidy.playlist',
    url: '/playlist/:uri'
    templateUrl: 'mopidy/templates/playlist.html'
    controller: ['$scope', 'playlist', ($scope, playlist) ->
      $scope.playlist = playlist
    ]
    resolve:
      playlist: ['$stateParams', 'mopidy', ($stateParams, mopidy) ->
        mopidy.getPlaylist $stateParams.uri
      ]
]

.factory 'debounce', ['$rootScope', ($rootScope) ->
  (wait, fn) ->
    _.debounce (args...) ->
      context = this
      $rootScope.$apply -> fn.apply context, args
    , wait
]

.service 'mopidy', ['$interval', '$exceptionHandler', 'butler', 'debounce',
 ($interval, $exceptionHandler, butler, debounce) ->
    mopidy =
      state: 'stopped'
      currentTlTrack: null
      timePosition: 0

    timer = null
    lastUpdate = null

    updateTimer = ->
      $interval.cancel timer
      lastUpdate = _.now()
      if mopidy.state is 'playing'
        timer = $interval ->
          mopidy.timePosition += _.now() - lastUpdate
          lastUpdate = _.now()
        , 100

    updateInterval = 50

    setState = debounce updateInterval, (state) ->
      old = mopidy.state
      mopidy.state = state
      updateTimer()

    setCurrentTlTrack = debounce updateInterval, (track) ->
      mopidy.currentTlTrack = track

    setTimePosition = debounce updateInterval, (position) ->
      mopidy.timePosition = position
      updateTimer()

    fetch = (method, setter) ->
      butler.call method
        .then setter, $exceptionHandler

    sync = ->
      fetch 'mopidy.playback.get_state', setState
      fetch 'mopidy.playback.get_current_tl_track', setCurrentTlTrack
      fetch 'mopidy.playback.get_time_position', setTimePosition

    sync()
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
      butler.call method, args...
      .then null, (err) ->
        sync()
        $exceptionHandler err

    mopidy.play = ->
      mopidy.state = 'playing'
      save 'mopidy.playback.play'

    mopidy.pause = ->
      mopidy.state = 'paused'
      save 'mopidy.playback.pause'

    mopidy.next = -> save 'mopidy.playback.next'
    mopidy.previous = -> save 'mopidy.playback.previous'

    mopidy.seek = (position) ->
      mopidy.timePosition = position
      save 'mopidy.playback.seek', position

    mopidy.getPlaylists = () ->
      butler.call 'mopidy.playlists.get_playlists', false

    mopidy.getPlaylist = (uri) ->
      butler.call 'mopidy.playlists.lookup', uri

    mopidy.queueTrack = (track) ->
      butler.call 'mopidy.tracklist.get_tl_tracks'
      .then (tlTracks) ->
        tlids = (tlTrack.tlid for tlTrack in tlTracks)
        index = 1 + tlids.indexOf mopidy.currentTlTrack?.tlid
        butler.call 'mopidy.tracklist.add', [track], index
      .then null, $exceptionHandler

    mopidy.setTracklist = (tracks, track) ->
      butler.call 'mopidy.playback.stop', true
      .then -> butler.call 'mopidy.tracklist.clear'
      .then -> butler.call 'mopidy.tracklist.add', tracks
      .then -> butler.call 'mopidy.tracklist.get_tl_tracks'
      .then (tlTracks) ->
        for tlTrack in tlTracks when tlTrack.track.uri is track.uri
          break
        butler.call 'mopidy.playback.play', tlTrack if tlTrack?
      .then null, $exceptionHandler

    return mopidy
]

.controller 'MopidyCtrl', ['$scope', 'mopidy', ($scope, mopidy) ->
  $scope.mopidy = mopidy
  return
]

.controller 'TracklistCtrl', ['$scope', '$ionicActionSheet', 'mopidy',
  ($scope, $ionicActionSheet, mopidy) ->
    $scope.trackAction = (track, tracks) ->
      buttons = [
        text: 'Queue'
        action: -> mopidy.queueTrack track
      ]

      if tracks
        buttons.push
          text: 'Play all from here'
          action: -> mopidy.setTracklist tracks, track

      $ionicActionSheet.show
        buttons: buttons
        cancelText: 'Cancel'
        buttonClicked: (index) ->
          buttons[index].action()
          true

    return
]

.controller 'SearchCtrl', ['$scope', 'mopidy', ($scope, mopidy) ->
  $scope.search =
    query: ''

  $scope.clear = ->
    $scope.search.query = ''

  return
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
      $scope.mopidy.state is 'playing'
    , (playing) ->
      $scope.playing = playing

    $scope.toggle = ->
      if $scope.playing
        $scope.mopidy.pause()
      else
        $scope.mopidy.play()
  ]

.directive 'mopidyNextButton', ->
  restrict: 'E'
  replace: true
  template: '''
    <button class="button button-icon icon ion-ios7-skipforward"
      ng-click="mopidy.next()">
    </button>
    '''

.directive 'mopidyPreviousButton', ->
  restrict: 'E'
  replace: true
  template: '''
    <button class="button button-icon icon ion-ios7-skipbackward"
      ng-click="mopidy.previous()">
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
        on-touch="startSeek()"
        on-release="endSeek()">
      <i>{{slider.length | time}}</i>
    </div>
    '''
  controller: ['$scope', ($scope) ->
    seeking = false

    $scope.slider =
      position: 0
      length: 0

    $scope.$watch ->
      $scope.mopidy.timePosition
    , (position) ->
      $scope.slider.position = position unless seeking

    $scope.$watch ->
      $scope.mopidy.currentTlTrack?.track.length
    , (length) ->
      $scope.slider.length = length or 0

    $scope.startSeek = -> seeking = true

    $scope.endSeek = ->
      seeking = false
      $scope.mopidy.seek $scope.slider.position
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
      butler.call 'lastfm.album.getInfo',
        album: album.name
        artist: album.artists[0].name
      .then (data) ->
        for image in data.album?.image or []
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

.directive 'mopidyTracklist', ->
  restrict: 'E'
  replace: true
  scope:
    tracks: '='
  templateUrl: 'mopidy/templates/tracklist.html'
  controller: 'TracklistCtrl'

.directive 'mopidyPlaybackBar', ->
  restrict: 'E'
  replace: true
  scope: false
  templateUrl: 'mopidy/templates/playback-bar.html'
  controller: 'MopidyCtrl'

.directive 'integer', ->
  restrict: 'A'
  require: 'ngModel'
  link: (scope, element, attrs, ctrl) ->
    ctrl.$parsers.unshift parseInt

.directive 'stopEvent', ->
  restrict: 'A'
  link: (scope, element, attrs) ->
    element.bind attrs.stopEvent, (event) ->
      event.stopPropagation()
      event.preventDefault()

.filter 'time', ->
  (input) ->
    seconds = (input / 1000) | 0
    "#{seconds // 60 }:#{('0' + seconds % 60).slice -2}"

.filter 'pluck', -> _.pluck

.filter 'join', ->
  (input, delimeter) -> (input or []).join delimeter or ' '
