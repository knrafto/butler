fs = require 'fs'

module.exports = ->
  config = require "#{process.env.HOME}/.config/butler/butler.conf"
  for file in fs.readdirSync 'services'
    name = file[...file.lastIndexOf '.']
    (require "./services/#{name}") config[name]
  return
