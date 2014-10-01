# An event and method bus that allows components to dynamically communicate.
module.exports = class Butler
  constructor: -> @reset()

  walk = (name) ->
    parts = name.split '.'
    for i in [parts.length..0]
      name: name
      prefix: parts[0...i].join '.'
      suffix: parts[i...].join('.')

  remove = (lst, e) ->
    i = lst.indexOf e
    lst.splice i, 1 unless i is -1

  # Register a handler for an event. Events are namespaced, so a handler for
  # 'foo' will receive events 'foo', 'foo.bar', 'foo.bar.baz', etc. To listen
  # to all events, listen to ''. Handler functions will be passed a context
  # as 'this' and any arguments passed to emit() or broadcast().
  on: (name, fn) ->
    @handlers[name] ?= []
    @handlers[name].push fn
    this

  # Unregister a handler for an event.
  off: (name, fn) ->
    remove @handlers[name], fn if @handlers[name]?
    this

  # Call handlers for an event and all events below it. For example, emitting
  # 'foo.bar.baz' will call handlers for '', 'foo', 'foo.bar', and
  # 'foo.bar.baz', in that order.
  emit: (name, args...) ->
    fns = []
    for context in walk name
      for fn in @handlers[context.prefix] or []
        fns.push [fn, context]
    fn.apply context, args for [fn, context] in fns
    this

  # Register a delegate function for a method. Methods are namespaced, so if a
  # method 'foo.bar.baz' is called, the methods 'foo.bar.baz', 'foo.bar',
  # 'foo', and '' will be searched until a delegate is found. Delegates will
  # be passed a context as 'this' and any arguments passed to call() or
  # apply().
  register: (name, fn) ->
    @delegates[name] = fn
    this

  # Unregister a delegate function for a method.
  unregister: (name) ->
    @delegates[name] = null
    this

  # Call a method. If for example a method 'foo.bar.baz' is called, the
  # methods 'foo.bar.baz', 'foo.bar', 'foo', and '' will be searched until a
  # delegate is found. If no delegate is found, returns 'undefined'.
  call: (name, args...) ->
    for context in walk name
      delegate = @delegates[context.prefix]
      return delegate.apply context, args if delegate?
    return

  # Remove all handlers and delegates.
  reset: ->
    @handlers = {}
    @delegates = {}
    this
