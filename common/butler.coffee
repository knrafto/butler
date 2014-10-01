# An event and method bus that allows components to dynamically communicate.
module.exports = class Butler
  constructor: -> @reset()

  walk = (name) ->
    parts = name.split '.'
    for i in [parts.length..0]
      name: name
      prefix: parts[0...i].join '.'
      suffix: parts[i...].join('.')

  # Register a handler for an event. Events are namespaced, so a handler for
  # 'foo' will receive events 'foo', 'foo.bar', 'foo.bar.baz', etc. To listen
  # to all events, listen to ''. Handler functions will be passed a context
  # as 'this' and any arguments passed to emit() or broadcast().
  # @param {string} name The event name.
  # @param {function(this:Context, ...)} fn The handler function.
  on: (name, fn) ->
    handlers = @handlers[name];
    if handlers then handlers.push(fn) else @handlers[name] = [fn];
    return @

  # Unregister a handler for an event.
  # @param {string} name The event name.
  # @param {function(this:Context, ...)} fn The handler function.
  off: (name, fn) ->
    handlers = @handlers[name];
    if handlers
      i = handlers.indexOf fn;
      handlers.splice i, 1 if i > -1
    return @

  # Call handlers for an event and all events below it. For example, emitting
  # 'foo.bar.baz' will call handlers for '', 'foo', 'foo.bar', and
  # 'foo.bar.baz', in that order.
  # @param {string} name The event name.
  # @param {...*} args The handler function arguments.
  emit: (name, args...) ->
    fns = []
    for context in walk name
      handlers = @handlers[context.prefix]
      if handlers?
        for fn in handlers
          fns.push([fn, context])
    for [fn, context] in fns
      fn.apply context, args
    return @

  # Register a delegate function for a method. Methods are namespaced, so if a
  # method 'foo.bar.baz' is called, the methods 'foo.bar.baz', 'foo.bar',
  # 'foo', and '' will be searched until a delegate is found. Delegates will
  # be passed a context as 'this' and any arguments passed to call() or
  # apply().
  # @param {string} name The method name.
  # @param {function(this:Context, ...)} fn The delegate function.
  register: (name, fn) ->
    @delegates[name] = fn
    return @

  # Unregister a delegate function for a method.
  # @param {string} name The method name.
  unregister: (name) ->
    @delegates[name] = null
    return @

  # Call a method. If for example a method 'foo.bar.baz' is called, the
  # methods 'foo.bar.baz', 'foo.bar', 'foo', and '' will be searched until a
  # delegate is found. If no delegate is found, returns 'undefined'.
  # @param {string} name The method name.
  # @param {...*} args The delegate function arguments.
  # @return {?} The method result.
  call: (name, args...) ->
    for context in walk name
      delegate = @delegates[context.prefix]
      return delegate.apply(context, args) if delegate?
    return

  # Remove all handlers and delegates.
  reset: ->
    @handlers = {}
    @delegates = {}
    return @
