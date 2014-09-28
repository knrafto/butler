var gulp = require('gulp');
var browserify = require('browserify');
var buffer = require('vinyl-buffer');
var clean = require('gulp-clean');
var concat = require('gulp-concat');
var source = require('vinyl-source-stream');
var templateCache = require('gulp-angular-templatecache');

gulp.task('clean', function () {
  gulp.src('dist', { read: false })
  .pipe(clean());
});

gulp.task('common', function() {
});

gulp.task('js', function() {
  browserify({
    standalone: 'common',
    entries: '../common'
  })
  .bundle()
  .pipe(source('common.js'))
  .pipe(buffer())
  .pipe(gulp.dest('dist/js'));

  gulp.src([
    'components/ionic/release/js/ionic.bundle.js',
    'components/underscore/underscore.js'
  ])
  .pipe(concat('lib.js'))
  .pipe(gulp.dest('dist/js'));

  gulp.src('app/**/*.js')
  .pipe(concat('bundle.js'))
  .pipe(gulp.dest('dist/js'));
});

gulp.task('html', function() {
  gulp.src('app/index.html')
  .pipe(gulp.dest('dist/'));

  gulp.src(['app/**/*.html', '!app/index.html'])
  .pipe(templateCache({ standalone: true }))
  .pipe(gulp.dest('dist/js'));
});

gulp.task('css', function() {
  gulp.src('components/ionic/release/css/ionic.css')
  .pipe(gulp.dest('dist/css'));
});

gulp.task('assets', function() {
  gulp.src('components/ionic/release/fonts/*')
  .pipe(gulp.dest('dist/fonts'));
})

gulp.task('watch', ['build'], function() {
  var express = require('express');
  var refresh = require('gulp-livereload');
  var livereload = require('connect-livereload');
  var livereloadPort = 35729;
  var serverPort = 5000;

  var server = express();
  server.use(livereload({port: livereloadPort}));
  server.use(express.static('./dist'));
  server.listen(serverPort);
  refresh.listen(livereloadPort);

  // TODO: watchify
  gulp.watch(['../common/**/*.js', 'app/**/*.js'], ['js']);
  gulp.watch('app/**/*.html', ['html']);

  gulp.watch('dist/**').on('change', refresh.changed);
});

gulp.task('build', ['js', 'html', 'css', 'assets']);

gulp.task('default', function () {
  gulp.start('watch');
});
