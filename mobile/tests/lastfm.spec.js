describe('lastfm', function() {
  var $httpBackend, butler, lastfm;

  beforeEach(module('lastfm'));

  beforeEach(inject(function(_$httpBackend_, $q, _butler_) {
    $httpBackend = _$httpBackend_;
    butler = _butler_;
    butler.register('key.lastfm', function() {
      var deferred = $q.defer();
      deferred.resolve('xxx');
      return deferred.promise;
    });
  }));

  beforeEach(inject(function(_lastfm_) {
    lastfm = _lastfm_;
  }));

  afterEach(function() {
    butler.reset();
  });

  it('should get a track image', function(done) {
    var track = {
      artists: [
        { name: 'foo' },
      ],
      album: { name: 'bar' }
    };

    $httpBackend.expectGET(
      'http://ws.audioscrobbler.com/2.0/?' +
      'album=bar&' +
      'api_key=xxx&' +
      'artist=foo&' +
      'method=album.getInfo'
    ).respond({
      album: {
        image: [
          {
            '#text': 'http://www.example.com/small',
            size: 'small'
          },
          {
            '#text': 'http://www.example.com/mega',
            size: 'mega'
          }
        ],
      }
    });

    lastfm.getTrackImage(track).then(function(url) {
      expect(url).toBe('http://www.example.com/mega');
    });

    $httpBackend.flush();
    $httpBackend.verifyNoOutstandingExpectation();
  });
});
