var duties = [
  'player',
  'spotify'
];

angular.module('butler', duties.concat(['ionic']))

.config(function($stateProvider) {
  $stateProvider.state('butler', {
    url: '/butler',
    abstract: true,
    templateUrl: 'templates/menu.html',
    controller: function($scope) {
      $scope.duties = duties;
    }
  });
})

.filter('capitalize', function(){
  return function(value) {
    return value.charAt(0).toUpperCase() + value.slice(1);
  };
});
