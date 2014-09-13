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
      server: server,
      state: init
    });
  }));

  it('should initialize scope', function() {
    expect($scope.state).toEqual(init);
  });

  it('should listen for data', function() {
    server.emit('player.state', [], data);
    expect($scope.state).toEqual(data);
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
    $scope.state = {};
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

    $scope.state.playing = true;
    $scope.toggle();
    expect(server.post).toHaveBeenCalledWith('player.play', [false]);

    $scope.state.playing = false;
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
      expect(timeFilter(601000)).toBe('10:01');
    });
  });
});
