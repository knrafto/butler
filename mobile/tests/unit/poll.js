describe('poll', function() {
  var poll, httpBackend, timeout;

  beforeEach(module('poll'));

  beforeEach(inject(function(_poll_, $httpBackend, $timeout) {
    poll = _poll_;
    httpBackend = $httpBackend;
    timeout = $timeout;
  }));

  it('should respond with received counter', function() {
    httpBackend.whenGET('http://example.com/').respond({
      counter: 2,
      foo: 'bar'
    });
    httpBackend.whenGET('http://example.com/?counter=2').respond({
      counter: 3,
      foo: 'baz'
    })
    poll('http://example.com/', function(data) {
      if (data.counter == 2) {
        expect(data.foo).toEqual('bar');
      } else if (data.counter == 3) {
        expect(data.foo).toEqual('baz');
      } else {
        expect(true).toBe(false);
      }
    });
    httpBackend.flush();
    timeout.flush();
    httpBackend.flush();
  });

  it('should retry on error', function() {
    var last_counter = null;
    var root = httpBackend.whenGET('http://example.com/')
    root.respond({
      counter: 2
    });
    httpBackend.whenGET('http://example.com/?counter=2').respond(500, {})
    poll('http://example.com/', function(data) {
      last_counter = data.counter;
    });
    httpBackend.flush();
    timeout.flush();
    httpBackend.flush();
    timeout.flush();
    root.respond({
      counter: 3
    });
    httpBackend.flush();
    expect(last_counter).toBe(3);
  });
})
