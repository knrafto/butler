fs = require 'fs'

module.exports = (config) ->
  fs.readdir __dirname, (err, files) ->
    throw err if err
    for filename in files:
      return if filename is 'index.js'
      name = filename.replace /\.js/, ''
      require('./' + name) config[name]
