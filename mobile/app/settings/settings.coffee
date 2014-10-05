angular.module('settings', ['core'])

.config ['$stateProvider', ($stateProvider) ->
  $stateProvider

  .state 'app.settings',
    url: '/settings'
    templateUrl: 'settings/settings.html'
]

.directive 'setting', ->
  restrict: 'E'
  replace: true
  scope:
    key: '@'
    name: '@'
  template: '''
    <div ng-click="edit()">
      {{name}}
      <span class="item-note">{{value}}</span>
    </div>
    '''

  controller: 'SettingCtrl'

.controller 'SettingCtrl', ['$scope', '$ionicModal', 'settings',
  ($scope, $ionicModal, settings) ->
    $scope.value = settings.get $scope.key
    $scope.edit = {}

    $ionicModal.fromTemplateUrl 'settings/edit.html',
        scope: $scope
        animation: 'slide-in-up'
      .then (modal) ->
        $scope.modal = modal

    $scope.edit = ->
      $scope.edit.value = $scope.value
      $scope.modal.show()

    $scope.save = ->
      $scope.value = $scope.edit.value
      settings.set $scope.key, $scope.value
      $scope.modal.hide()

    $scope.$on '$destroy', ->
      $scope.modal.remove()

    return
]
