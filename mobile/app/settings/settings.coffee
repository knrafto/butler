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

.controller 'SettingCtrl', ['$scope', '$ionicPopup', 'settings',
  ($scope, $ionicPopup, settings) ->
    $scope.value = settings.get $scope.key
    $scope.input =
      value: ''

    $scope.edit = ->
      $scope.input.value = $scope.value
      $ionicPopup.show
        template: '''<input ng-model="input.value">'''
        title: $scope.name
        scope: $scope
        buttons: [
          text: 'Cancel'
        ,
          text: 'Save',
          type: 'button-positive',
          onTap: ->
            $scope.value = $scope.input.value
            console.log $scope.value
            settings.set $scope.key, $scope.value
        ]

    return
]
