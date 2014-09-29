require('request');

function Server() {
  this.expectations = {};
}

Server.prototype.expect = function(url, data, statusCode, err) {
  this.expectations[url] = {
    statusCode: statusCode || 200,
    error: err,
    data: data
  };
};

Server.prototype.respond = function(url, callback) {
  var response = this.expectations[url];
  delete this.expectations[url];
  if (!response) {
    throw new Error('Unexpected request ' + url);
  }
  callback(response.error, { statusCode: response.statusCode }, response.data);
};

Server.prototype.flush = function() {
  expect(this.expectations).toEqual({});
  this.expectations = {};
};

var server = new Server();

var request = function(options, callback) {
  if (!options.json) {
    throw new Error('Not a JSON request');
  }
  return server.respond(options.url, callback);
};

require.cache[require.resolve('request')].exports = request;
var API = require('../api');
delete require.cache[require.resolve('request')];
delete require.cache[require.resolve('../api')];

describe('API', function() {
  var api;
  var response = { result: 42 };

  beforeEach(function() {
    api = new API({
      url: 'http://example.com',
      params: { key: 'foo' },
      max: 3
    });
  });

  afterEach(function() {
    server.flush();
  });

  it('should request JSON data', function(done) {
    server.expect('http://example.com?key=foo', response);
    api.get().then(function(data) {
      expect(data).toBe(response);
      done();
    });
  });

  it('should encode URL parameters', function(done) {
    server.expect('http://example.com?value=bar%20baz&key=foo', response);
    api.get({ value: 'bar baz' }).then(function(data) {
      expect(data).toBe(response);
      done();
    });
  });

  it('should cache results in an LRU cache', function(done) {
    server.expect('http://example.com?key=foo', response);
    api.get().then(function(data) {
      expect(data).toBe(response);
      api.get().then(function(data) {
        expect(data).toBe(response);
        done();
      });
    });
  });

  it('should reject on error', function(done) {
    server.expect('http://example.com?key=foo', response, 200, new Error());
    api.get().then(undefined, function(err) {
      expect(err).toBeTruthy();
      done();
    });
  });

  it('should reject on non-200 response', function(done) {
    server.expect('http://example.com?key=foo', response, 404);
    api.get().then(undefined, function(err) {
      expect(err).toBeTruthy();
      done();
    });
  });
});
