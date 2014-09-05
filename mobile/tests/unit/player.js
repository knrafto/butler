describe('controller: PlayerCtrl', function() {
  var $scope, $httpBackend;

  var data = {
    playing: false,
    current_track: 5,
    queue: [4, 5, 6],
    history: [1, 2, 3]
  };

  beforeEach(module('butler'));
  beforeEach(module('templates'));

  beforeEach(function() {
    var mockPoll = function(path, callback) {
      callback(data);
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

  it('should poll for data', function() {
    expect($scope.playing).toEqual(data.playing);
    expect($scope.current_track).toEqual(data.current_track);
    expect($scope.queue).toEqual(data.queue);
    expect($scope.history).toEqual(data.history);
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

    $httpBackend.expectPOST(
      'http://www.example.com/player/play',
      {pause: false}
    ).respond(200, '');
    $scope.play(false);
    $httpBackend.flush();

    $httpBackend.expectPOST(
      'http://www.example.com/player/play',
      {pause: true}
    ).respond(200, '');
    $scope.play(true);
    $httpBackend.flush();

    $httpBackend.expectPOST(
      'http://www.example.com/player/seek',
      {seek: 4.5}
    ).respond(200, '');
    $scope.seek(4.5);
    $httpBackend.flush();
  });
});

describe('filter: time', function() {
  beforeEach(module('butler'));

  it('should convert a number to time', function() {
    inject(function(timeFilter) {
      expect(timeFilter(0.6)).toBe('0:00');
      expect(timeFilter(250)).toBe('4:10');
      expect(timeFilter(6000)).toBe('100:00');
    });
  });
});
