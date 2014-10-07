gulp          = require 'gulp'
gutil         = require 'gulp-util'
browserify    = require 'browserify'
buffer        = require 'vinyl-buffer'
clean         = require 'gulp-clean'
coffee        = require 'gulp-coffee'
coffeeify     = require 'coffeeify'
coffeelint    = require 'gulp-coffeelint'
concat        = require 'gulp-concat'
sass          = require 'gulp-sass'
source        = require 'vinyl-source-stream'
sourcemaps    = require 'gulp-sourcemaps'
templateCache = require 'gulp-angular-templatecache'

paths =
  lib: [
    'components/angular/angular.js'
    'components/angular-animate/angular-animate.js'
    'components/angular-sanitize/angular-sanitize.js'
    'components/angular-ui-router/release/angular-ui-router.js'
    'components/ionic/release/js/ionic.js'
    'components/ionic/release/js/ionic-angular.js'
    'components/underscore/underscore.js'
  ]
  common: '../common'
  bundle: 'app/**/*.coffee'
  index: 'index.html'
  templates: 'app/**/*.html'
  css: 'components/ionic/release/css/ionic.css'
  sass: 'app/**/*.scss'
  fonts: 'components/ionic/release/fonts/*'

gulp.task 'clean', ->
  gulp.src 'www',
    read: false
  .pipe clean()

gulp.task 'lib', ->
  gulp.src paths.lib
  .pipe concat 'lib.js'
  .pipe gulp.dest 'www/js'

gulp.task 'common', ->
  browserify
    standalone: 'common'
    extensions: ['.coffee']
    entries: paths.common
  .transform coffeeify
  .bundle()
  .pipe source 'common.js'
  .pipe buffer()
  .pipe gulp.dest 'www/js'

gulp.task 'bundle', ->
  # TODO: uglify with other files
  gulp.src paths.bundle
  .pipe sourcemaps.init()
  .pipe coffee bare: true
    .on 'error', gutil.log
  .pipe concat 'bundle.js'
  .pipe sourcemaps.write '.'
  .pipe gulp.dest 'www/js'

gulp.task 'index', ->
  gulp.src paths.index
  .pipe gulp.dest 'www/'

gulp.task 'templates', ->
  gulp.src paths.templates
  .pipe templateCache standalone: true
  .pipe gulp.dest 'www/js'

gulp.task 'css', ->
  gulp.src paths.css
  .pipe gulp.dest 'www/css'

gulp.task 'sass', ->
  gulp.src paths.sass
  .pipe sass()
  .pipe concat 'bundle.css'
  .pipe gulp.dest 'www/css'

gulp.task 'fonts', ->
  gulp.src paths.fonts
  .pipe gulp.dest 'www/fonts'

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
  server.use livereload port: livereloadPort
  server.use express.static './www'
  server.listen serverPort
  refresh.listen livereloadPort

  gulp.watch 'www/**'
    .on 'change', refresh.changed

  # TODO: watchify
  for task in buildTasks
    gulp.watch paths[task], [task]

gulp.task 'default', -> gulp.start 'watch'
