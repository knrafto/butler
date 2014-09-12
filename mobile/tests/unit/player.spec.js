describe('PlayerCtrl', function() {
  var $scope, server;

  var init = {
    playing: false,
    current_track: null,
    queue: [],
    history: []
  };

  var data = {
    playing: false,
    current_track: 4,
    queue: [4, 5, 6],
    history: [1, 2, 3]
  };

  beforeEach(module('player'));
  beforeEach(module('templates'));

  beforeEach(inject(function(EventEmitter, $rootScope, $controller) {
    server = new EventEmitter;

    $scope = $rootScope.$new();
    $controller('PlayerCtrl', {
      $scope: $scope,
      server: server
    });
  }));

  it('should initialize scope', function() {
    angular.forEach(init, function(value, key) {
      expect($scope[key]).toEqual(value);
    });
  });

  it('should listen for data', function() {
    server.emit('player.state', [], data);
    angular.forEach(data, function(value, key) {
      expect($scope[key]).toEqual(value);
    });
  });

  it('should stop listening on destroy', function() {
    $scope.$destroy();
    expect(server.hasListeners('player.state')).toBe(false);
  });
});

describe('PlaybackCtrl', function() {
  var $scope, server;


  beforeEach(module('player'));
  beforeEach(module('templates'));

  beforeEach(inject(function(EventEmitter, $rootScope, $controller) {
    server = {post: null};
    EventEmitter(server);
    spyOn(server, 'post');

    $scope = $rootScope.$new();
    $controller('PlaybackCtrl', {
      $scope: $scope,
      server: server
    });
  }));

  it('should post button commands', function() {
    $scope.nextTrack();
    expect(server.post).toHaveBeenCalledWith('player.next_track');
    $scope.prevTrack();
    expect(server.post).toHaveBeenCalledWith('player.prev_track');

    $scope.playing = true;
    $scope.toggle();
    expect(server.post).toHaveBeenCalledWith('player.play', [false]);

    $scope.playing = false;
    $scope.toggle();
    expect(server.post).toHaveBeenCalledWith('player.play', [true]);
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
