var EventEmitter = require('events').EventEmitter;
var Q = require('q');
var WebSocket = require('ws');
var util = require('util');
var _ = require('underscore');

var butler = require('../butler');

function Connection(address, options) {
  var self = this;
  var timeoutInterval = 2000;
  var reconnectInterval = 5000;

  this.nextId = 0;
  this.pending = {};

  function receive(response) {
    var deferred = self.pending[response.id];
    delete self.pending[response.id];
    if (!deferred) {
      self.emit('error', new Error('unexpected response ' + response));
      return;
    }
    if (response.error) {
      deferred.reject(response.error);
    } else {
      deferred.resolve(response.result);
    }
  }

  function cancelAll() {
    _.each(self.pending, function(deferred) {
      deferred.reject(err);
    });
    self.pending = {};
  }

  function connect() {
    var ws = self.ws = new WebSocket(address, options);

    var timeout = setTimeout(function() {
      ws.close();
    }, timeoutInterval);

    ws.on('open', function() {
      clearTimeout(timeout);
      self.emit('open');
    });

    ws.on('close', function(code, message) {
      clearTimeout(timeout);
      cancelAll();
      this.ws = null;
      self.emit('close', code, message);
      setTimeout(connect, reconnectInterval);
    });

    ws.on('message', function(data) {
      try {
        data = JSON.parse(data);
        if (data.event) {
          var event = data.event;
          delete data.event;
          self.emit('event', event, data);
        } else {
          receive(data);
        }
      } catch (err) {
        self.emit('error', err);
      }
    });

    ws.on('error', function(err) {
      self.emit('error', err);
    });
  }

  connect();
}

util.inherits(Connection, EventEmitter);

Connection.prototype.request = function(method, params) {
  if (!this.ws) {
    throw new Error('WebSocket is not connected');
  }
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
    this.emit('error', err);
  }
  this.pending[requestId] = deferred;
  return deferred.promise;
};

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

var methods = {
  play: 'core.playback.play',
  pause: 'core.playback.pause',
  previous: 'core.playback.previous',
  next: 'core.playback.next',
  seek: 'core.playback.seek',

  queueTrack: function(track) {
    var index = 0;
    if (state.currentTlTrack) {
      var tlid = state.currentTlTrack.tlid;
      _.find(state.tracklist, function(tlTrack, i) {
        if (tlTrack.tlid === tlid) {
          index = i + 1;
          return true;
        }
      });
    }
    return connection.request('core.tracklist.add', {
      tracks: [track],
      at_position: index
    });
  },

  setTracklist: function(tracks, track) {
    return connection.request('core.playback.stop', {
        clear_current_track: true
    }).then(function() {
      connection.request('core.tracklist.clear');
    }).then(function() {
      return connection.request('core.tracklist.add', { tracks: tracks });
    }).then(function() {
      return connection.request('core.tracklist.get_tl_tracks');
    }).then(function(tlTracks) {
      var tlTrack = _.find(tlTracks, function(tlTrack) {
        return tlTrack.track.uri === track.uri;
      });
      return connection.request('core.playback.play', {
        tl_track: tlTrack
      });
    });
  },

  sync: sync
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
  butler.emit('mopidy.update', state);
}

module.exports = function(config) {
  config = config || {};
  connection = new Connection(config.url);

  butler.register('mopidy', function() {
    var method = methods[this.method.replace(/^mopidy\./, '')];
    return _.isString(method)
      ? connection.request(method, _.toArray(arguments))
      : method.apply(null, arguments);
  });

  connection.on('error', mopidyError);

  connection.on('open', function() {
    butler.emit('mopidy.connect');
    sync();
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
