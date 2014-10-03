# Reconnect after exponential backoff.
module.exports = class Reconnect
  constructor: (@start) ->
    @attempts = 1
    @timeout = null
    @start()

  start: -> @start()

  success: ->
    clearTimeout @timeout
    @attempts = 1
    this

  retry: ->
    clearTimeout @timeout
    interval = Math.min (2 ** @attempts - 1) * 1000, 15000
    @timeout = setTimeout =>
      @attempts++
      @start()
    , Math.random() * interval
    this
