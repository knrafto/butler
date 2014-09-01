module.exports = function(config){
  config.set({

    basePath : '../',

    files : [
      'www/lib/ionic/js/angular/angular.js',
      'www/lib/ionic/js/angular/angular-animate.js',
      'www/lib/ionic/js/angular/angular-mocks.js',
      'www/lib/ionic/js/angular/angular-sanitize.min.js',
      'www/lib/ionic/js/angular-ui/angular-ui-router.js',
      'www/lib/ionic/js/ionic.js',
      'www/lib/ionic/js/ionic-angular.min.js',
      'www/js/*.js',
      'tests/unit/*.js'
    ],

    autoWatch : true,

    frameworks: ['jasmine'],

    browsers : ['Chrome'],

    plugins : [
      'karma-chrome-launcher',
      'karma-jasmine'
    ],

    junitReporter : {
      outputFile: 'test_out/unit.xml',
      suite: 'unit'
    }

  });
};
