var fs = require('fs');
var process = require('process');
var _ = require('underscore');

var services = require('./services');

var config_path = process.env['HOME'] + '/.config/butler/butler.cfg';

fs.readFile(config_path, 'utf8', function(err, data) {
  if (err) throw err;
  var config = JSON.parse(data);
  _.each(services.all, function(service) {
    var name = service.name;
    service.start(config[name]);
  });
});
