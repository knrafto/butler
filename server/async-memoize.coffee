Q = require 'q'

module.exports = (cache, id, fn) ->
  [id, fn] = [null, id] unless fn
  (args...) ->
    key = if id then id args... else args[0]
    value = cache.get key
    return value if value?
    promise = Q.try -> fn args...
    cache.set key, promise
    promise.then null, (err) ->
      cache.del key
      throw err
