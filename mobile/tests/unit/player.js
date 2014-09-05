describe('controller: PlayerCtrl', function() {
  var $scope, $httpBackend, pollCallback;

  var init = {
    playing: false,
    position: 0,
    current_track: null,
    queue: [],
    history: []
  };

  var data = {
    playing: false,
    position: 314,
    current_track: 4,
    queue: [4, 5, 6],
    history: [1, 2, 3]
  };

  beforeEach(module('butler'));
  beforeEach(module('templates'));

  beforeEach(function() {
    var mockPoll = function(path, callback) {
      pollCallback = callback;
    };

    inject(function($rootScope, $controller, _$location_, _$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $scope = $rootScope.$new();
      $controller('PlayerCtrl', {
          $scope: $scope,
          poll: mockPoll,
          SERVER_URL: 'http://www.example.com'
      });
    });
  });

  it('should initialize scope', function() {
    angular.forEach(init, function(value, key) {
      expect($scope[key]).toEqual(value);
    });
    expect($scope.slider.position).toEqual($scope.position);
  });

  it('should poll for data', function() {
    pollCallback(data);
    angular.forEach(data, function(value, key) {
      expect($scope[key]).toEqual(value);
    });
    expect($scope.slider.position).toEqual($scope.position);
  });

  it('should post commands', function() {
    $httpBackend.expectPOST('http://www.example.com/player/next_track')
      .respond(200, '');
    $scope.nextTrack();
    $httpBackend.flush();

    $httpBackend.expectPOST('http://www.example.com/player/prev_track')
      .respond(200, '');
    $scope.prevTrack();
    $httpBackend.flush();

    $scope.playing = false;
    $httpBackend.expectPOST(
      'http://www.example.com/player/play',
      {pause: false}
    ).respond(200, '');
    $scope.toggle();
    $httpBackend.flush();

    $scope.playing = true;
    $httpBackend.expectPOST(
      'http://www.example.com/player/play',
      {pause: true}
    ).respond(200, '');
    $scope.toggle();
    $httpBackend.flush();

    $scope.slider.position = 314;
    $httpBackend.expectPOST(
      'http://www.example.com/player/seek',
      {seek: 314}
    ).respond(200, '');
    $scope.seek();
    $httpBackend.flush();
  });
});

describe('filter: time', function() {
  beforeEach(module('butler'));

  it('should convert a number to time', function() {
    inject(function(timeFilter) {
      expect(timeFilter(600)).toBe('0:00');
      expect(timeFilter(250000)).toBe('4:10');
      expect(timeFilter(600000)).toBe('10:00');
    });
  });
});
