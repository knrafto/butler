var gulp = require('gulp');
var gutil = require('gulp-util');
var browserify = require('browserify');
var buffer = require('vinyl-buffer');
var clean = require('gulp-clean');
var coffee = require('gulp-coffee');
var coffeelint = require('gulp-coffeelint');
var concat = require('gulp-concat');
var sass = require('gulp-sass');
var source = require('vinyl-source-stream');
var sourcemaps = require('gulp-sourcemaps');
var templateCache = require('gulp-angular-templatecache');

var paths = {
  lib: [
    'components/ionic/release/js/ionic.bundle.js',
    'components/underscore/underscore.js'
  ],
  common: '../common',
  bundle: 'app/**/*.coffee',
  index: 'app/index.html',
  templates: [
    'app/**/*.html',
    '!app/index.html'
  ],
  css: 'components/ionic/release/css/ionic.css',
  sass: 'app/**/*.scss',
  fonts: 'components/ionic/release/fonts/*'
};

gulp.task('clean', function() {
  gulp.src('dist', { read: false })
  .pipe(clean());
});

gulp.task('lib', function() {
  gulp.src(paths.lib)
  .pipe(concat('lib.js'))
  .pipe(gulp.dest('dist/js'));
});

gulp.task('common', function() {
  browserify({
    standalone: 'common',
    entries: paths.common
  })
  .bundle()
  .pipe(source('common.js'))
  .pipe(buffer())
  .pipe(gulp.dest('dist/js'));
});

gulp.task('bundle', function() {
  gulp.src(paths.bundle)
  .pipe(coffee({ bare: true })).on('error', gutil.log)
  .pipe(sourcemaps.write('./maps'))
  .pipe(concat('bundle.js'))
  .pipe(gulp.dest('dist/js'));
});

gulp.task('index', function() {
  gulp.src(paths.index)
  .pipe(gulp.dest('dist/'));
});

gulp.task('templates', function() {
  gulp.src(paths.templates)
  .pipe(templateCache({ standalone: true }))
  .pipe(gulp.dest('dist/js'));
});

gulp.task('css', function() {
  gulp.src(paths.css)
  .pipe(gulp.dest('dist/css'));
});

gulp.task('sass', function() {
  gulp.src(paths.sass)
  .pipe(sass())
  .pipe(concat('bundle.css'))
  .pipe(gulp.dest('dist/css'));
});

gulp.task('fonts', function() {
  gulp.src(paths.fonts)
  .pipe(gulp.dest('dist/fonts'));
});

gulp.task('lint', function () {
    gulp.src(paths.bundle)
    .pipe(coffeelint())
    .pipe(coffeelint.reporter())
});

var buildTasks = [
  'lib', 'common', 'bundle', 'index', 'templates', 'css', 'sass', 'fonts'
];

gulp.task('build', buildTasks);

gulp.task('watch', buildTasks, function() {
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
  gulp.watch('dist/**').on('change', refresh.changed);

  // TODO: watchify
  buildTasks.forEach(function(task) {
    gulp.watch(paths[task], [task]);
  });
});

gulp.task('default', function () {
  gulp.start('watch');
});
