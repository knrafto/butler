var _ = require('underscore');

var services = [
  'console', 'exit', 'mopidy', 'server', 'socket.io'
];

exports.start = function(config) {
  var started = {};
  var starting = {};

  function start(name) {
    if (started[name]) return;
    if (starting[name]) {
      throw new Error('cyclic dependencies: ' + name);
    }
    starting[name] = true;
    var service = require('./' + name);
    _.each(service.depends, function(depend) {
      start(depend);
    });
    service.start(config[name]);
    delete starting[name]
    started[name] = true;
  }

  _.each(services, function(name) {
    start(name);
  });
}
