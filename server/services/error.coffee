butler = require '../butler'

module.exports = ->
  butler.on 'error', (err) ->
    console.log err.stack
