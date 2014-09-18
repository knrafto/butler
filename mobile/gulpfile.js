var gulp = require('gulp');
var gutil = require('gulp-util');
var bower = require('bower');
var concat = require('gulp-concat');
var sass = require('gulp-sass');
var minifyCss = require('gulp-minify-css');
var rename = require('gulp-rename');
var sh = require('shelljs');
var karma = require('gulp-karma');

var paths = {
  sass: ['./scss/**/*.scss'],
  js: [
    './www/lib/ionic/js/ionic.bundle.js',
    './www/lib/socket.io-client/socket.io.js',
    './www/lib/underscore/underscore.js',
    '../common/butler.js',
    './www/js/*.js'
  ]
};

gulp.task('default', ['sass', 'test']);

gulp.task('test', function() {
  var action = gulp.env.watch ? 'watch' : 'run';
  return gulp.src('failed-match-*')
    .pipe(karma({
      configFile: 'karma.conf.js',
      action: action
    }));
});

gulp.task('sass', function() {
  if (gulp.env.watch) {
    return gulp.watch(paths.sass, ['sass']);
  }
  return gulp.src('./scss/ionic.app.scss')
    .pipe(sass())
    .pipe(gulp.dest('./www/css/'))
    .pipe(minifyCss({
      keepSpecialComments: 0
    }))
    .pipe(rename({ extname: '.min.css' }))
    .pipe(gulp.dest('./www/css/'));
});

gulp.task('js', function() {
  if (gulp.env.watch) {
    return gulp.watch(paths.js, ['js']);
  }
  return gulp.src(paths.js)
    .pipe(concat('all.js'))
    .pipe(gulp.dest('./www/dist/'));
});

gulp.task('install', ['git-check'], function() {
  return bower.commands.install()
    .on('log', function(data) {
      gutil.log('bower', gutil.colors.cyan(data.id), data.message);
    });
});

gulp.task('git-check', function(done) {
  if (!sh.which('git')) {
    console.log(
      '  ' + gutil.colors.red('Git is not installed.'),
      '\n  Git, the version control system, is required to download Ionic.',
      '\n  Download git here:', gutil.colors.cyan('http://git-scm.com/downloads') + '.',
      '\n  Once git is installed, run \'' + gutil.colors.cyan('gulp install') + '\' again.'
    );
    process.exit(1);
  }
  done();
});
