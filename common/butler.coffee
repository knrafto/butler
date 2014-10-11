# An event and method bus that allows components to dynamically communicate.
module.exports = class Butler
  constructor: ->
    @handlers = {}
    @delegates = {}

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
  on: (name, fn) ->
    @handlers[name] ?= []
    @handlers[name].push fn

  # Call handlers for an event and all events below it. For example, emitting
  # 'foo.bar.baz' will call handlers for '', 'foo', 'foo.bar', and
  # 'foo.bar.baz' in an unspecified order.
  emit: (name, args...) ->
    for context in walk name
      for fn in @handlers[context.prefix] or []
        fn.apply context, args

  # Register a delegate function for a method. Methods are namespaced, so if a
  # method 'foo.bar.baz' is called, the methods 'foo.bar.baz', 'foo.bar',
  # 'foo', and '' will be searched until a delegate is found. Delegates will
  # be passed a context as 'this' and any arguments passed to call() or
  # apply().
  register: (name, fn) ->
    @delegates[name] = fn

  # Call a method. If for example a method 'foo.bar.baz' is called, the
  # methods 'foo.bar.baz', 'foo.bar', 'foo', and '' will be searched until a
  # delegate is found. If no delegate is found, returns 'undefined'.
  call: (name, args...) ->
    for context in walk name
      delegate = @delegates[context.prefix]
      return delegate.apply context, args if delegate?
    return
