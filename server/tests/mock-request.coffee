expectations = {}

request = (options, callback) ->
  throw new Error 'Not a JSON request' unless options.json
  url = options.url
  response = expectations[url]
  delete expectations[url]
  throw new Error "Unexpected request #{url}" unless response
  callback response.error, (statusCode: response.statusCode), response.data

request.expect = (url) ->
  respond: (data, statusCode) ->
    expectations[url] =
      data: data
      statusCode: statusCode or 200
  error: (err) ->
    expectations[url] = error: err

request.flush = ->
  if expectations.length
    throw new Error "Unresolved expectations: #{expectations}"

module.exports = request
