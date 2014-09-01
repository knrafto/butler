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
    httpBackend.whenGET('http://example.com/').respond(500, {});
    poll('http://example.com/', function(data) {
      expect(true).toBe(false);
    });
    httpBackend.flush();
    timeout.flush();
    httpBackend.flush();
  });
})
