module.exports = class Action
  constructor: (@fn) ->
    @timeoutId = null

  callNow: (args...) ->
    @cancel()
    @fn args...

  callLater: (delay, args...) ->
    @cancel()
    @timeoutId = setTimeout (=> @callNow args...), delay

  cancel: ->
    clearTimeout @timeoutId
