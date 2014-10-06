module.exports = class Action
  constructor: (@fn) ->
    @timeoutId = null

  run: (delay, args...) ->
    @cancel()
    @timeoutId = setTimeout (=> @fn args...), delay

  cancel: ->
    clearTimeout @timeoutId
