Butler = require '../butler'

# An Agency is where spies are created
class Agency
  constructor: ->
    @spies = {}
    @calls = []

  spy: (name) ->
    unless @spies[name]?
      agency = @
      @spies[name] = (args...) ->
        agency.calls.push
          spy: name
          object: @
          args: args
        return name
    return @spies[name]

makeCall = (spy, name, prefix, suffix, args) ->
  spy: spy
  object:
    name: name
    prefix: prefix
    suffix: suffix
  args: args or []

describe 'Butler', ->
  butler = null
  agency = null

  beforeEach ->
    butler = new Butler
    agency = new Agency

  describe 'on', ->
    it 'should add listeners', ->
      butler.on 'foo', agency.spy 'one'
      butler.on 'foo', agency.spy 'two'

      butler.emit 'foo', 1
      butler.emit 'bar', 2
      butler.emit 'foo', 3

      expect(agency.calls).toEqual [
        makeCall 'one', 'foo', 'foo', '', [1]
        makeCall 'two', 'foo', 'foo', '', [1]
        makeCall 'one', 'foo', 'foo', '', [3]
        makeCall 'two', 'foo', 'foo', '', [3]
      ]

  describe 'off', ->
    it 'should remove listeners', ->
      butler.on 'foo', agency.spy 'one'
      butler.on 'foo', agency.spy 'two'
      butler.on 'foo', agency.spy 'three'
      butler.off 'foo', agency.spy 'two'

      butler.emit 'foo'

      expect(agency.calls).toEqual [
        makeCall 'one', 'foo', 'foo', ''
        makeCall 'three', 'foo', 'foo', ''
      ]

    it 'should work when called from an event', ->
      butler.on 'foo.bar', ->
        butler.off 'foo.bar', agency.spy 'one'
        butler.off 'foo', agency.spy 'two'
      butler.on 'foo.bar', agency.spy 'one'
      butler.on 'foo', agency.spy 'two'

      butler.emit 'foo.bar'
      butler.emit 'foo.bar'

      expect(agency.calls).toEqual [
        makeCall 'one', 'foo.bar', 'foo.bar', ''
        makeCall 'two', 'foo.bar', 'foo', 'bar'
      ]

  describe 'emit', ->
    it 'should fire all listeners in order', ->
      butler.on '', agency.spy 'one'
      butler.on 'foo', agency.spy 'two'
      butler.on 'foo.bar', agency.spy 'three'
      butler.on 'foo.baz', agency.spy 'four'

      butler.emit 'foo.bar', 1, 2

      expect(agency.calls).toEqual [
        makeCall 'three', 'foo.bar', 'foo.bar', '', [1, 2]
        makeCall 'two', 'foo.bar', 'foo', 'bar', [1, 2]
        makeCall 'one', 'foo.bar', '', 'foo.bar', [1, 2]
      ]

  describe 'register', ->
    it 'should set a delegate', ->
      butler.register 'foo', agency.spy 'one'
      butler.register 'foo', agency.spy 'two'

      result = butler.call 'foo', 1

      expect(result).toEqual 'two'
      expect(agency.calls).toEqual [
        makeCall 'two', 'foo', 'foo', '', [1]
      ]

  describe 'unregister', ->
    it 'should remove a delegate', ->
      butler.register 'foo', agency.spy 'one'
      butler.register 'foo', agency.spy 'two'
      butler.unregister 'foo'

      result = butler.call 'foo'

      expect(result).toBeUndefined()
      expect(agency.calls).toEqual []

  describe 'call', ->
    it 'should fire the last delegate', ->
      butler.register '', agency.spy 'one'
      butler.register 'foo', agency.spy 'two'
      butler.register 'foo.bar', agency.spy 'three'
      butler.register 'foo.baz', agency.spy 'four'

      results = [
        butler.call 'baz', 1, 2
        butler.call 'foo', 3, 4
        butler.call 'foo.bar.baz', 5, 6
      ]

      expect(results).toEqual ['one', 'two', 'three']
      expect(agency.calls).toEqual [
        makeCall 'one', 'baz', '', 'baz', [1, 2]
        makeCall 'two', 'foo', 'foo', '', [3, 4]
        makeCall 'three', 'foo.bar.baz', 'foo.bar', 'baz', [5, 6]
      ]

  describe 'reset', ->
    it 'should remove all handlers', ->
      butler.on 'foo', agency.spy 'one'
      butler.on 'foo', agency.spy 'two'
      butler.on 'bar', agency.spy 'three'
      butler.reset()

      butler.emit 'foo'
      butler.emit 'bar'

      expect(agency.calls).toEqual []

    it 'should remove all delegates', ->
      butler.register 'foo', agency.spy 'one'
      butler.register 'foo', agency.spy 'two'
      butler.register 'bar', agency.spy 'three'
      butler.reset()

      results = [
        butler.call 'foo'
        butler.call 'bar'
      ]

      expect(results).toEqual [undefined, undefined]
      expect(agency.calls).toEqual []
