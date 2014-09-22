var fs = require('fs');
var _ = require('underscore');

module.exports = function(config) {
  fs.readdir(__dirname, function(err, files) {
    if (err) throw err;
    _.each(files, function(filename) {
      if (filename === 'index.js') return;
      var name = filename.replace(/\.js/, '');
      require('./' + name)(config[name]);
    });
  });
};
