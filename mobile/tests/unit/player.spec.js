describe('controller: PlayerCtrl', function() {
  var $scope, $interval, $httpBackend, pollCallback,
      cancelled = false;

  var init = {
    counter: null,
    playing: false,
    position: 0,
    current_track: null,
    queue: [],
    history: []
  };

  var data = {
    counter: 2,
    playing: false,
    position: 314,
    current_track: 4,
    queue: [4, 5, 6],
    history: [1, 2, 3]
  };

  beforeEach(module('player'));
  beforeEach(module('templates'));

  beforeEach(inject(function($rootScope, $controller, _$httpBackend_, _$interval_) {
    function poll(path, callback) {
      pollCallback = callback;
    }

    poll.cancel = function() {
      cancelled = true;
    }

    $httpBackend = _$httpBackend_;
    $interval = _$interval_;
    $scope = $rootScope.$new();
    $controller('PlayerCtrl', {
      $scope: $scope,
      poll: poll,
      SERVER_URL: 'http://example.com'
    });
  }));

  it('should initialize scope', function() {
    angular.forEach(init, function(value, key) {
      expect($scope[key]).toEqual(value);
    });
  });

  it('should poll for data', function() {
    pollCallback(data);
    angular.forEach(data, function(value, key) {
      expect($scope[key]).toEqual(value);
    });
  });

  it('should cancel on destroy', function() {
    $scope.$destroy();
    expect(cancelled).toBe(true);
  });
});

describe('controller: PlaybackCtrl', function() {
  var $scope, $interval, $httpBackend;

  beforeEach(module('player'));
  beforeEach(module('templates'));

  beforeEach(inject(function($rootScope, $controller, _$interval_, _$httpBackend_) {
    $scope = $rootScope.$new();
    $interval = _$interval_
    $httpBackend = _$httpBackend_;
    $controller('PlaybackCtrl', {
      $scope: $scope,
      SERVER_URL: 'http://example.com'
    });
  }));

  it('should post commands', function() {
    $httpBackend.expectPOST('http://example.com/player/next_track')
      .respond(200, '');
    $scope.nextTrack();
    $httpBackend.flush();

    $httpBackend.expectPOST('http://example.com/player/prev_track')
      .respond(200, '');
    $scope.prevTrack();
    $httpBackend.flush();

    $scope.playing = false;
    $httpBackend.expectPOST(
      'http://example.com/player/play',
      {pause: false}
    ).respond(200, '');
    $scope.toggle();
    $httpBackend.flush();

    $scope.playing = true;
    $httpBackend.expectPOST(
      'http://example.com/player/play',
      {pause: true}
    ).respond(200, '');
    $scope.toggle();
    $httpBackend.flush();

    $httpBackend.expectPOST(
      'http://example.com/player/seek',
      {seek: 314}
    ).respond(200, '');
    $scope.startSlide();
    $scope.slider.position = 314;
    $scope.endSlide();
    $httpBackend.flush();
  });

  it('should keep track of time', function() {
    $scope.position = 0;
    $scope.playing = true;
    $scope.$apply();

    $interval.flush(1000);
    expect($scope.slider.position).toEqual(1000);

    $httpBackend.expectPOST(
      'http://example.com/player/seek',
      {seek: 0}
    ).respond(200, '');
    $scope.startSlide();
    $scope.slider.position = 0;
    $interval.flush(1000);
    expect($scope.slider.position).toEqual(0);
    $scope.endSlide();
    $httpBackend.flush();

    $scope.playing = false;
    $scope.slider.position = 0;
    $interval.flush(1000);
    expect($scope.slider.position).toEqual(0);
  });

  it('should stop ticking on destroy', function() {
    $scope.position = 0;
    $scope.playing = true;
    $scope.$destroy();
    $scope.$apply();

    $interval.flush(1000);
    expect($scope.slider.position).toBeUndefined();
  });
});

describe('filter: time', function() {
  it('should format milliseconds', function() {
    module('player');
    inject(function(timeFilter) {
      expect(timeFilter(600)).toBe('0:00');
      expect(timeFilter(250000)).toBe('4:10');
      expect(timeFilter(600000)).toBe('10:00');
    });
  });
});
