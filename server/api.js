var LRU = require('lru-cache');
var Q = require('q');
var request = require('request');
var url = require('url');
var _ = require('underscore');

/**
 * A LRU cache of API results.
 * @constructor
 * @param options Cache options.
 */
function API(options) {
  this.url = options.url;
  this.params = options.params;
  this.cache = new LRU(options);
};

/**
 * Get JSON from a url.
 */
API.prototype.get = function(params) {
  params = _.extend({}, params, this.params);
  var requestUrl = this.url + url.format({ query: params });

  var cache = this.cache;
  var cached = cache.get(requestUrl);
  if (cached) return Q(cached);

  var deferred = Q.defer();
  request({ url: requestUrl, json: true }, function(err, response, body) {
    if (err) {
      deferred.reject(err);
    } else if (response.statusCode != 200) {
      deferred.reject(new Error(response.statusCode + ' ' + requestUrl));
    } else {
      cache.set(requestUrl, body);
      deferred.resolve(body);
    }
  });
  return deferred.promise;
};

/** @module API */
module.exports = API;
