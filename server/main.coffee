fs     = require 'fs'

Butler = require '../common/butler'

module.exports = ->
  butler = new Butler
  config = require "#{process.env.HOME}/.config/butler/butler.conf"
  for file in fs.readdirSync 'services'
    name = file[...file.lastIndexOf '.']
    (require "./services/#{name}") butler, config[name]
  return
