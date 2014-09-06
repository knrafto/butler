describe('service: poll', function() {
  var poll, $httpBackend, $timeout;

  beforeEach(module('poll'));

  beforeEach(inject(function(_poll_, _$httpBackend_, _$timeout_) {
    poll = _poll_;
    $httpBackend = _$httpBackend_;
    $timeout = _$timeout_;
  }));

  it('should call callback with data', function() {
    serverData = {
      counter: 1,
      foo: 'bar'
    };

    poll('http://example.com/', function(data) {
      expect(data).toEqual(serverData)
    });

    $httpBackend.expectGET('http://example.com/').respond(serverData);
    $timeout.flush();
    $httpBackend.flush();
  });

  it('should respond with received counter', function() {
    poll('http://example.com/', function() {});

    $httpBackend.expectGET('http://example.com/').respond({counter: 2});
    $timeout.flush();
    $httpBackend.flush();

    $httpBackend.expectGET('http://example.com/?counter=2').respond({counter: 3});
    $timeout.flush();
    $httpBackend.flush();
  });

  it('should reset on error', function() {
    poll('http://example.com/', function() {});

    $httpBackend.expectGET('http://example.com/').respond({counter: 2});
    $timeout.flush();
    $httpBackend.flush();

    $httpBackend.expectGET('http://example.com/?counter=2').respond(201, '');
    $timeout.flush();
    $httpBackend.flush();

    $httpBackend.expectGET('http://example.com/').respond({counter: 2});
    $timeout.flush();
    $httpBackend.flush();
  });

  it('should be cancellable during timeout', function() {
    promise = poll('http://example.com/', function() {
      throw Error('not reached');
    });

    poll.cancel(promise);
    $timeout.flush();
    $httpBackend.verifyNoOutstandingRequest();
  });

  it('should be cancellable during request', function () {
    promise = poll('http://example.com/', function() {
      throw Error('not reached');
    });

    $httpBackend.expectGET('http://example.com/').respond({counter: 2});
    $timeout.flush();
    poll.cancel(promise);
    expect($httpBackend.flush).toThrow(new Error('No pending request to flush !'));
  });
});
