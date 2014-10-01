butler  = require '../butler'
start   = require '../services/exit'

describe 'exit', ->
  one = null

  beforeEach ->
    one = jasmine.createSpy 'one'
    spyOn(process, 'exit').and.callFake (code) ->
      process.emit 'exit', code
    start()
    butler.on 'exit', one

  afterEach -> butler.reset()

  it 'should fire on exit', ->
    process.exit 1
    expect(one).toHaveBeenCalledWith 1

  it 'should fire on SIGINT', ->
    process.emit 'SIGINT'
    expect(one).toHaveBeenCalledWith 0
    expect(process.exit).toHaveBeenCalledWith 0

  it 'should fire on SIGTERM', ->
    process.emit 'SIGTERM'
    expect(one).toHaveBeenCalledWith 0
    expect(process.exit).toHaveBeenCalledWith 0
