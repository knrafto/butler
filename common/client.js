var EventEmitter = require('events').EventEmitter;
var util = require('util');
var WebSocket = require('ws');
var _ = require('underscore');

/**
 * Create a Client that connects to a remote server over a
 * websocket.
 * @constructor
 * @augments EventEmitter
 * @property {Boolean} connected The WebSocket connection state.
 */
function Client() {
  this.connected = false;
  this.ws = null;

  this.nextId = 0;
  this.requests = {};
}

util.inherits(Client, EventEmitter);

/**
 * Open the connection on the given url and protocols, closing any previous
 * connection. Upon a successful connection, the 'open' event will fire.
 * @param {string} url The server URL.
 * @param {(string|Array.<string>)=} protocols The protocols to use.
 */
Client.prototype.open = function(url, protocols) {
  this.close();

  this.forceClose = false;
  var ws = this.ws = new WebSocket(url, protocols);
  var self = this;

  ws.onopen = function() {
    self.connected = true;
    self.emit('open');
  };

  ws.onclose = function(event) {
    self.connected = false;
    self.ws = null;
    _.each(self.requests, function(callback) {
      callback(new Error('WebSocket closed'));
    });
    self.emit('close', event.code, event.reason);
  };

  ws.onmessage = function(event) {
    try {
      var message = JSON.parse(event.data);
      if (message.event != null) {
        self.emit('event', message.event, message);
      } else {
        var callback = self.requests[message.id];
        var error = message.error && new Error(message.error.message);
        if (callback) callback(error, message.result);
      }
    } catch (err) {
      self.emit('error', err);
    }
  };

  ws.onerror = function(event) {
    self.emit('error', event.errno);
  };
};

/**
 * Close the connection, if it exists. This will cancel any pending requests
 * and fire the 'close' event. The connection will not try to reconnect.
 */
Client.prototype.close = function() {
  if (this.ws) this.ws.close();
};

/**
 * Asynchronosly send a JSON-RPC request.
 * @param {string} method The method name.
 * @param {(Array|Object)} args The method arguments.
 * @param {function(Error, *)} callback The asynchronous callback.
 */
Client.prototype.request = function(method, args, callback) {
  try {
    if (!this.connected) throw new Error('WebSocket not connected');
    var requestId = this.nextId++;
    this.requests[requestId] = callback;
    this.ws.send(JSON.stringify({
      jsonrpc: '2.0',
      id: requestId,
      method: method,
      params: args
    }));
  } catch (err) {
    delete this.requests[requestId];
    callback(err, null);
  }
};

/** @module client */
module.exports = Client;
