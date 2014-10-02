fs = require 'fs'

start = (config) ->
  fs.readdir 'services', (err, files) ->
    throw err if err?
    for file in files
      name = file[...file.lastIndexOf '.']
      (require "./services/#{name}") config[name]
    return

module.exports = ->
  config_path = "#{process.env.HOME}/.config/butler/butler.conf"
  fs.readFile config_path, 'utf8', (err, data) ->
    throw err if err?
    start JSON.parse data
