Q       = require 'q'

memoize = require '../async-memoize'

class Cache
  constructor: (@cache = {}) ->

  get: (key) -> @cache[key]

  set: (key, value) -> @cache[key] = value

  del: (key) -> delete @cache[key]

  has: (key) -> @cache[key]?

describe 'async-memoize', ->
  it 'should call the function and cache values', (done) ->
    cache = new Cache
    wrapped = memoize cache, (str) -> Q str
    (wrapped 'foo').then (result) ->
      (expect result).toEqual 'foo'
      (expect cache.has 'foo').toBe true
      done()

  it 'should retrieve previously computed values', ->
    promise = Q.defer().promise
    cache = new Cache foo: promise
    wrapped = memoize cache, -> throw new Error 'Cache miss'
    (expect wrapped 'foo').toBe promise

  it 'should delete from the cache on error', (done) ->
    deferred = Q.defer()
    cache = new Cache
    wrapped = memoize cache, -> deferred.promise
    deferred.reject new Error 'bam'
    (wrapped 'foo').then null, (err) ->
      (expect err).toBeTruthy()
      (expect cache.has 'foo').toBe false
      done()

  it 'should use the key function if provided', (done) ->
    cache = new Cache
    wrapped = memoize cache, ((a, b) -> "#{a} #{b}"), (a, b) -> a + b
    (wrapped 1, 2).then (result) ->
      (expect result).toEqual 3
      (expect cache.has '1 2').toBe true
      done()

