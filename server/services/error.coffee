module.exports = (butler) ->
  butler.on 'error', (err) ->
    console.log err.stack
