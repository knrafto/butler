gulp = require 'gulp'
gutil = require 'gulp-util'
browserify = require 'browserify'
buffer = require 'vinyl-buffer'
clean = require 'gulp-clean'
coffee = require 'gulp-coffee'
coffeelint = require 'gulp-coffeelint'
concat = require 'gulp-concat'
sass = require 'gulp-sass'
source = require 'vinyl-source-stream'
sourcemaps = require 'gulp-sourcemaps'
templateCache = require 'gulp-angular-templatecache'

paths =
  lib: [
    'components/ionic/release/js/ionic.bundle.js'
    'components/underscore/underscore.js'
  ]
  common: '../common'
  bundle: 'app/**/*.coffee'
  index: 'app/index.html'
  templates: [
    'app/**/*.html'
    '!app/index.html'
  ]
  css: 'components/ionic/release/css/ionic.css'
  sass: 'app/**/*.scss'
  fonts: 'components/ionic/release/fonts/*'

gulp.task 'clean', ->
  gulp.src 'dist',
    read: false
  .pipe clean()

gulp.task 'lib', ->
  gulp.src paths.lib
  .pipe concat 'lib.js'
  .pipe gulp.dest 'dist/js'

gulp.task 'common', ->
  browserify
    standalone: 'common'
    entries: paths.common
  .bundle()
  .pipe source 'common.js'
  .pipe buffer()
  .pipe gulp.dest 'dist/js'

gulp.task 'bundle', ->
  gulp.src paths.bundle
  .pipe coffee(bare: true)
  .on 'error', gutil.log
  .pipe sourcemaps.write './maps'
  .pipe concat 'bundle.js'
  .pipe gulp.dest 'dist/js'

gulp.task 'index', ->
  gulp.src paths.index
  .pipe gulp.dest 'dist/'

gulp.task 'templates', ->
  gulp.src paths.templates
  .pipe templateCache(standalone: true)
  .pipe gulp.dest 'dist/js'

gulp.task 'css', ->
  gulp.src paths.css
  .pipe gulp.dest 'dist/css'

gulp.task 'sass', ->
  gulp.src paths.sass
  .pipe sass()
  .pipe concat 'bundle.css'
  .pipe gulp.dest 'dist/css'

gulp.task 'fonts', ->
  gulp.src paths.fonts
  .pipe gulp.dest 'dist/fonts'

gulp.task 'lint', ->
  gulp.src paths.bundle
  .pipe coffeelint()
  .pipe coffeelint.reporter()

buildTasks = [
  'lib'
  'common'
  'bundle'
  'index'
  'templates'
  'css'
  'sass'
  'fonts'
]

gulp.task 'build', buildTasks

gulp.task 'watch', buildTasks, ->
  express = require 'express'
  refresh = require 'gulp-livereload'
  livereload = require 'connect-livereload'

  livereloadPort = 35729
  serverPort = 5000
  server = express()
  server.use livereload(port: livereloadPort)
  server.use express.static './dist'
  server.listen serverPort
  refresh.listen livereloadPort
  gulp.watch('dist/**').on 'change', refresh.changed

  # TODO: watchify
  for task in buildTasks
    gulp.watch paths[task], [task]

gulp.task 'default', -> gulp.start 'watch'
