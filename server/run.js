#!/usr/bin/env node
require('coffee-script/register');
var fs = require('fs');

var config_path = process.env['HOME'] + '/.config/butler/butler.conf';

fs.readFile(config_path, 'utf8', function(err, data) {
  if (err) throw err;
  require('./services')(JSON.parse(data));
});
