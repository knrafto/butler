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
  this.readyState = Client.CLOSED;
  this.ws = null;

  this.nextId = 0;
  this.requests = {};
}

util.inherits(Client, EventEmitter);

_.each(['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'], function(state, index) {
  Client.prototype[state] = Client[state] = index;
});

/**
 * Open the connection on the given url and protocols, closing any previous
 * connection. Upon a successful connection, the 'open' event will fire.
 * @param {string} url The server URL.
 */
Client.prototype.open = function(url) {
  this.close();

  var ws = this.ws = new WebSocket(url);
  this.readyState = Client.CONNECTING;
  var self = this;

  ws.onopen = function() {
    self.readyState = Client.OPEN;
    self.emit('open');
  };

  ws.onclose = function(event) {
    self.readyState = Client.CLOSED;
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

  ws.onerror = function() {
    self.emit('error', new Error('WebSocket error'));
  };
};

/**
 * Close the connection, if it exists. This will cancel any pending requests
 * and fire the 'close' event. The connection will not try to reconnect.
 */
Client.prototype.close = function(code, reason) {
  if (!this.ws) return;
  this.readyState = Client.CLOSING;
  this.ws.close(code, reason);
};

/**
 * Asynchronosly send a JSON-RPC request.
 * @param {string} method The method name.
 * @param {(Array|Object)} args The method arguments.
 * @param {function(Error, *)} callback The asynchronous callback.
 */
Client.prototype.request = function(method, args, callback) {
  if (this.readyState != Client.OPEN) {
    throw new Error('Client not connected');
  }
  var requestId = this.nextId++;
  this.requests[requestId] = callback;
  this.ws.send(JSON.stringify({
    jsonrpc: '2.0',
    id: requestId,
    method: method,
    params: args
  }));
};

/** @module client */
module.exports = Client;
