angular.module('underscore', [])

.factory('_', function($window) {
  return $window._;
});
