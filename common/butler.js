(function(isNode, isAngular) {
  'use strict';

  function butler(_) {

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

    function Butler() {
      this.reset();
    }

    Butler.prototype = {
      on: function(name, fn) {
        if (!fn) {
          fn = name;
          name = '';
        }
        var handlers = this.handlers[name] || (this.handlers[name] = []);
        handlers.push(fn);
        return this;
      },

      off: function(name, fn) {
        if (!fn) {
          fn = name;
          name = '';
        }
        var handlers = this.handlers[name];
        if (handlers) {
          var i = handlers.indexOf(fn);
          if (i > -1) handlers.splice(i, 1);
        }
        return this;
      },

      emit: function(name) {
        var handlers = this.handlers;
        var context = { event: name }; // TODO: make suffix available
        var args = _.toArray(arguments).slice(1);
        var fns = _.chain(walk(name))
          .map(function(prefix) { return handlers[prefix]; })
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
        this.delegates[name] = fn;
        return this;
      },

      unregister: function(name) {
        if (!name) name = '';
        this.delegates[name] = null;
        return this;
      },

      call: function(name) {
        var delegates = this.delegates;
        var context = { method: name }; // TODO: make suffix available
        var args = _.toArray(arguments).slice(1);
        var delegate = _.chain(walk(name))
          .reverse()
          .map(function(prefix) { return delegates[prefix]; })
          .find(_.identity)
          .value();
        if (!delegate) notFound(name);
        return delegate.apply(context, args);
      },

      reset: function() {
        this.handlers = {};
        this.delegates = {};
      }
    };

    return new Butler();
  }

  if (isNode) {
    module.exports = butler(require('underscore'));
  } else if (isAngular) {
    angular.module('butler', [])
    .factory('butler', ['$window', function($window) {
      return butler($window._);
    }]);
  }

}(typeof module !== 'undefined' && module.exports,
  typeof angular !== 'undefined'));
