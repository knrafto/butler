assert = require 'assert'

sinon  = require 'sinon'

Action = require '../action'

describe 'Action', ->
  fn = null
  action = null
  clock = null

  beforeEach ->
    fn = sinon.spy()
    action = new Action fn
    clock = sinon.useFakeTimers()

  afterEach ->
    clock.restore()

  describe '#run', ->
    it 'should run the function with arguments after a delay', ->
      action.run 100, 'foo', 'bar'
      clock.tick 99
      assert.equal fn.called, false
      clock.tick 1
      assert fn.calledWith 'foo', 'bar'

    it 'should cancel previously scheduled calls', ->
      action.run 100, 'foo', 'bar'
      clock.tick 99
      assert.equal fn.called, false
      action.run 100, 'foo', 'baz'
      clock.tick 99
      assert.equal fn.called, false
      clock.tick 1
      assert fn.calledWith 'foo', 'baz'

  describe '#cancel', ->
    it 'should cancel scheduled calls', ->
      action.run 100, 'foo', 'bar'
      clock.tick 99
      action.cancel()
      clock.tick 1
      assert.equal fn.called, false
