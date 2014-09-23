var EventEmitter = require('events').EventEmitter;
var util = require('util');
var Q = require('q');
var Websocket = require('ws');
var _ = require('underscore');

var butler = require('../butler');

function Connection(url) {
  var ws = this.ws = new Websocket(url);
  var self = this;

  this.nextId = 0;
  this.pending = {};

  ws.on('error', function(err) {
    self._error(err);
  });

  ws.on('open', function() {
    self.emit('open');
  });

  ws.on('close', function(code, message) {
    self._cancelAll();
    self.emit('close', code, message);
  });

  ws.on('message', function(message) {
    try {
      var data = JSON.parse(message);
      if (data.event) {
        var event = data.event;
        delete data.event;
        self.emit('event', event, data);
      } else {
        self._receive(data);
      }
    } catch (err) {
      self._error(err);
    }
  });
}

util.inherits(Connection, EventEmitter);

_.extend(Connection.prototype, {
  request: function(method, params) {
    var requestId = this.nextId++;
    var deferred = Q.defer();
    var request = {
        id: requestId,
        jsonrpc: '2.0',
        method: method,
        params: params || {}
    };
    try {
      this.ws.send(JSON.stringify(request));
    } catch (err) {
      this._error(err);
    }
    this.pending[requestId] = deferred;
    return deferred.promise;
  },

  _receive: function(response) {
    var deferred = this.pending[response.id];
    delete this.pending[response.id];
    if (!deferred) {
      this._error(new Error('unexpected response ' + response));
      return;
    }
    if (response.error) {
      deferred.reject(response.error);
    } else {
      deferred.resolve(response.result);
    }
  },

  _cancelAll: function() {
    _.each(this.pending, function(deferred) {
      deferred.reject(err);
    });
    this.pending = {};
  },

  _error: function(err) {
    this.emit('error', err);
  }
});

var connection;
var state = {};

var syncMethods = {
  currentTlTrack: 'core.playback.get_current_tl_track',
  playlists: 'core.playlists.get_playlists',
  random: 'core.tracklist.get_random',
  repeat: 'core.tracklist.get_repeat',
  single: 'core.tracklist.get_single',
  state: 'core.playback.get_state',
  timePosition: 'core.playback.get_time_position',
  tracklist: 'core.tracklist.get_tl_tracks'
};

var events = {
  playback_state_changed: function(data) {
    state.state = data.new_state;
    notify();
  },

  track_playback_started: function(data) {
    state.currentTlTrack = data.tl_track;
    state.timePosition = 0;
    notify();
  },

  track_playback_stopped: function(data) {
    state.currentTlTrack = data.tl_track;
    state.timePosition = data.time_position;
    notify();
  },

  seeked: function(data) {
    state.timePosition = data.time_position;
    notify();
  },

  tracklist_changed: function() {
    sync(['tracklist']);
  },

  options_changed: function() {
    sync(['random', 'repeat', 'single']);
  },

  playlist_changed: function() {
    sync(['playlists']);
  },

  playlists_loaded: function() {
    sync(['playlists']);
  }
};

function mopidyError(err) {
  butler.emit('log.error', 'mopidy', err);
}

function sync(properties) {
  properties = properties || _.keys(syncMethods);
  var promises = _.map(properties, function(property) {
    return connection.request(syncMethods[property])
      .then(function(value) {
        state[property] = value;
      });
  });
  Q.all(promises).done(notify, mopidyError);
}

function notify() {
  butler.emit('mopidy.state', state);
}

module.exports = function(config) {
  config = config || {};
  connection = new Connection(config.url);

  butler.register('mopidy', function(params) {
    var method = this.method
      .replace(/^mopidy./, '')
      .replace(/([a-z])([A-Z])/g, function(match, p1, p2) {
        return p1 + '_' + p2.toLowerCase();
      });
    return connection.request(method, params);
  });

  connection.on('error', mopidyError);

  connection.on('open', function() {
    sync();
    butler.emit('mopidy.connect');
  });

  connection.on('close', function(code, message) {
    butler.emit('mopidy.disconnect', code, message);
  });

  connection.on('event', function(event, data) {
    var handler = events[event];
    if (!handler) return;
    try {
      handler(data);
    } catch (err) {
      mopidyError(err);
    }
  });
};
