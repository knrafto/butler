var fs = require('fs');
var process = require('process');

var services = require('./services');

var config_path = process.env['HOME'] + '/.config/butler/butler.conf';

fs.readFile(config_path, 'utf8', function(err, data) {
  if (err) throw err;
  services.start(JSON.parse(data));
});
