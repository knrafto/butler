var fs = require('fs');
var process = require('process');

var butler = require('./butler');
var servants = require('./servants');

var config_path = process.env['HOME'] + '/.config/butler/butler.cfg';

fs.readFile(config_path, 'utf8', function(err, data) {
  if (err) {
    console.log('Error: ' + err);
    return;
  }

  var config = JSON.parse(data);
  var butler = new butler.Butler(config);
  servants.all.forEach(function(servant) {
    butler.hire(servant);
  });
});
