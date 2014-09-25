var _ = require('underscore');

/**
 * An event or method context.
 * @typedef Context
 * @property {string} name The event or method name.
 * @property {string} prefix The event or method name prefix that this
 *     function was registered on.
 * @property {string} suffix The rest of the name.
 */

/**
 * Split a name into contexts, longest to shortest.
 * @param {string} name The name to walk.
 * @return {Array.<Context>} The result contexts.
 */
function walk(name) {
  var parts = name.split('.');
  var contexts = [];
  return _.map(_.range(parts.length, -1, -1), function(i) {
     return {
      name: name,
      prefix: parts.slice(0, i).join('.'),
      suffix: parts.slice(i).join('.')
    };
  });
}

/**
 * An event and method bus that allows components to dynamically communicate.
 * @constructor
 */
function Butler() {
  this.reset();
}

/**
 * Register a handler for an event. Events are namespaced, so a handler for
 * 'foo' will receive events 'foo', 'foo.bar', 'foo.bar.baz', etc. To listen
 * to all events, listen to ''. Handler functions will be passed a context
 * as 'this' and any arguments passed to emit() or broadcast().
 * @param {string} name The event name.
 * @param {function(this:Context, ...)} fn The handler function.
 */
Butler.prototype.on = function(name, fn) {
  var handlers = this.handlers[name];
  handlers ? handlers.push(fn) : this.handlers[name] = [fn];
};

/**
 * Unregister a handler for an event.
 * @param {string} name The event name.
 * @param {function(this:Context, ...)} fn The handler function.
 */
Butler.prototype.off = function(name, fn) {
  var handlers = this.handlers[name];
  if (handlers) {
    var i = handlers.indexOf(fn);
    if (i > -1) handlers.splice(i, 1);
  }
};

/**
 * Call handlers for an event and all events below it. For example, emitting
 * 'foo.bar.baz' will call handlers for '', 'foo', 'foo.bar', and
 * 'foo.bar.baz', in that order.
 * @param {string} name The event name.
 * @param {...*} args The handler function arguments.
 */
Butler.prototype.emit = function(name, args) {
  this.broadcast(name, _.toArray(arguments).slice(1));
};

/**
 * Call handlers for an event and all events below it. For example, emitting
 * 'foo.bar.baz' will call handlers for 'foo.bar.baz', 'foo.bar', 'foo', and
 * ''. If any handler throws an exception, the 'error' event is emitted.
 * @param {string} name The event name.
 * @param {Array} args The handler function arguments.
 */
Butler.prototype.broadcast = function(name, args) {
  var handlers = this.handlers;
  _.chain(walk(name))
    .map(function(context) {
      return _.map(handlers[context.prefix], function(fn) {
        return _.bind(fn, context);
      });
    })
    .flatten()
    .each(function(fn) {
      fn.apply(null, args);
    });
};

/**
 * Register a delegate function for a method. Methods are namespaced, so if a
 * method 'foo.bar.baz' is called, the methods 'foo.bar.baz', 'foo.bar',
 * 'foo', and '' will be searched until a delegate is found. Delegates will
 * be passed a context as 'this' and any arguments passed to call() or
 * apply().
 * @param {string} name The method name.
 * @param {function(this:Context, ...)} fn The delegate function.
 */
Butler.prototype.register = function(name, fn) {
  this.delegates[name] = fn;
};

/**
 * Unregister a delegate function for a method.
 * @param {string} name The method name.
 */
Butler.prototype.unregister = function(name) {
  this.delegates[name] = null;
};

/**
 * Call a method. If for example a method 'foo.bar.baz' is called, the
 * methods 'foo.bar.baz', 'foo.bar', 'foo', and '' will be searched until a
 * delegate is found. If no delegate is found, returns 'undefined'.
 * @param {string} name The method name.
 * @param {...*} args The delegate function arguments.
 * @return {?} The method result.
 */
Butler.prototype.call = function(name, args) {
  return this.apply(name, _.toArray(arguments).slice(1));
};

/**
 * Call a method. If for example a method 'foo.bar.baz' is called, the
 * methods 'foo.bar.baz', 'foo.bar', 'foo', and '' will be searched until a
 * delegate is found.
 * @param {string} name The method name.
 * @param {Array} args The delegate arguments.
 * @return {?} The method result.
 */
Butler.prototype.apply = function(name, args) {
  var delegates = this.delegates;
  var fn = _.chain(walk(name))
    .map(function(context) {
      var delegate = delegates[context.prefix];
      return delegate && _.bind(delegate, context);
    })
    .find(_.identity)
    .value();
  return fn && fn.apply(null, args);
};

/**
 * Remove all handlers and delegates.
 */
Butler.prototype.reset = function() {
  this.handlers = {};
  this.delegates = {};
};

/** @module butler */
module.exports = Butler;
