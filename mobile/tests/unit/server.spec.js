describe('service: server', function() {
  var $rootScope,
      server,
      socket,
      callbacks;

  function emit(name) {
    var args = Array.prototype.slice.call(arguments, 1);
    angular.forEach(callbacks[name] || [], function(f) {
      f.apply(null, args);
    });
  }

  beforeEach(module('server'));

  beforeEach(inject(function($window) {
    callbacks = {}
    socket = {
      emit: function() {},

      on: function(name, f) {
        (callbacks[name] = callbacks[name] || []).push(f);
      }
    };

    spyOn(socket, 'emit');

    $window.io = function(url) {
      return socket;
    };
  }));

  beforeEach(inject(function(_$rootScope_, _server_) {
    $rootScope = _$rootScope_;
    server = _server_;
  }));

  it('should emit events on a socket', function() {
    server.emit('foo.bar', [1, 2], {x: 3});
    expect(socket.emit).toHaveBeenCalledWith('event', {
      name: 'foo.bar',
      args: [1, 2],
      kwds: {x: 3}
    });

    server.emit('foo.bar');
    expect(socket.emit).toHaveBeenCalledWith('event', {
      name: 'foo.bar',
      args: [],
      kwds: {}
    });
  });

  it('should send requests', function() {
    server.post('foo.bar', [1, 2], {x: 3});
    expect(socket.emit).toHaveBeenCalledWith('request', {
      id: 0,
      method: 'foo.bar',
      args: [1, 2],
      kwds: {x: 3}
    });

    server.post('foo.bar');
    expect(socket.emit).toHaveBeenCalledWith('request', {
      id: 1,
      method: 'foo.bar',
      args: [],
      kwds: {}
    });
  });

  it('should respond to requests', function() {
    container = {
      success0: function() {},
      success1: function() {},
      success2: function() {},
      failure: function() {}
    };

    spyOn(container, 'success0');
    spyOn(container, 'success1');
    spyOn(container, 'success2');
    spyOn(container, 'failure');

    server.post('foo.bar').then(container.success0, container.failure);
    server.post('foo.baz').then(container.success1, container.failure);
    server.post('foo.quux').then(container.success2, container.failure);

    emit('response', {
      id: 10,
      result: 'result'
    });
    expect(container.success0).not.toHaveBeenCalled();
    expect(container.success1).not.toHaveBeenCalled();
    expect(container.success2).not.toHaveBeenCalled();

    emit('response', {
      id: 1,
      result: 'result'
    });
    $rootScope.$apply();
    expect(container.success1).toHaveBeenCalledWith('result');

    emit('response', {
      id: 2,
      result: 'result'
    });
    $rootScope.$apply();
    expect(container.success2).toHaveBeenCalledWith('result');

    emit('response', {
      id: 0,
      result: 'result'
    });
    $rootScope.$apply();
    expect(container.success0).toHaveBeenCalledWith('result');

    expect(container.failure).not.toHaveBeenCalled();
  });

  it('should reject requests on error', function() {
    container = {
      success: function() {},
      failure0: function() {},
      failure1: function() {}
    };

    spyOn(container, 'success');
    spyOn(container, 'failure0');
    spyOn(container, 'failure1');

    server.post('foo.bar').then(container.success, container.failure0);
    server.post('foo.baz').then(container.success, container.failure1);

    emit('error', 'SomeError', 'bam');
    $rootScope.$apply();
    expect(container.success).not.toHaveBeenCalled();
    expect(container.failure0).toHaveBeenCalledWith('SomeError: bam');
    expect(container.failure1).toHaveBeenCalledWith('SomeError: bam');
  });

  it('should subscribe to the server', function() {
    server.on('foo.bar', function() {});
    expect(socket.emit).toHaveBeenCalledWith('subscribe', {
      name: 'foo.bar'
    });
  });

  it('should call callbacks on an event', function() {
    container = {
      f: function() {}
    };

    spyOn(container, 'f');

    server.on('foo.bar', container.f);
    emit('event', {
      name: 'foo.bar',
      args: [1, 2],
      kwds: {x: 3}
    });
    expect(container.f).toHaveBeenCalledWith([1, 2], {x: 3});
  });

  it('should remove callbacks on an event', function() {
    container = {
      f: function() {}
    };

    spyOn(container, 'f');

    server.on('foo.bar', container.f);
    server.off('foo.bar', container.f);
    emit('event', {
      name: 'foo.bar',
      args: [1, 2],
      kwds: {x: 3}
    });
    expect(container.f).not.toHaveBeenCalled();
  });
});
