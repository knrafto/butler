var _ = require('underscore');

function walk(name) {
  var prefix = [];
  var prefixes = [''];
  _.each(name.split('.'), function(namePart) {
    prefix.push(namePart);
    prefixes.push(prefix.join('.'));
  });
  return prefixes;
}

function notFound(name) {
  throw new Error('no delegate for method "' + name + '"');
}

module.exports = {
  on: function(name, fn) {
    if (!fn) {
      fn = name;
      name = '';
    }
    this._events || (this._events = {});
    var events = this._events[name] || (this._events[name] = []);
    events.push(fn);
    return this;
  },

  off: function(name, fn) {
    if (!fn) {
      fn = name;
      name = '';
    }
    var events = this._events && this._events[name];
    if (events) {
      var i = events.indexOf(fn);
      if (i > -1) events.splice(i, 1);
    }
    return this;
  },

  emit: function(name) {
    var events = this._events;
    if (!events) return this;
    var context = { event: name };
    var args = _.toArray(arguments).slice(1);
    var fns = _.chain(walk(name))
      .map(function(prefix) { return events[prefix]; })
      .compact()
      .flatten()
      .value();
    _.each(_.toArray(fns), function(fn) {
      fn.apply(context, args);
    });
  },

  register: function(name, fn) {
    if (!fn) {
      fn = name;
      name = '';
    }
    this._delegates || (this._delegates = {});
    this._delegates[name] = fn;
    return this;
  },

  unregister: function(name) {
    if (!name) name = '';
    if (!this._delegates) return this;
    delete this._delegates[name];
    return this;
  },

  call: function(name) {
    var delegates = this._delegates;
    if (!delegates) notFound(name);
    var context = { method: name };
    var args = _.toArray(arguments).slice(1);
    var delegate = _.chain(walk(name))
      .map(function(prefix) { return delegates[prefix]; })
      .find(_.identity)
      .value();
    if (!delegate) notFound(name);
    return delegate.apply(context, args);
  }
};
