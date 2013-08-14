/*
 * VertNet app.
 */
define([
  'jquery',
  'underscore',
  'router',
  'spin',
  'mps'
], function ($, _, Router, Spin, mps) {

  var App = function () {
  }

  App.prototype.parseUrl = function() {
    var a = /\+/g;  // Regex for replacing addition symbol with a space
    var r = /([^&=]+)=?([^&]*)/g;
    var d = function (s) { return decodeURIComponent(s.replace(a, " ")); };
    var q = window.location.search.substring(1);
    var urlParams = {};
    
    // Parses URL parameters:
    while ((e = r.exec(q))) {
      urlParams[d(e[1])] = d(e[2]);
    }

    return urlParams;
  }

  App.prototype.update = function (profile) {
    this.profile = new Backbone.Model(profile);
  }

  return {
   init: function () {
      var app = new App;
      var target = $('#main-spinner').get(0);
      var options = {
        lines: 5, // The number of lines to draw
        length: 40, // The length of each line
        width: 6, // The line thickness
        radius: 5, // The radius of the inner circle
        corners: 1, // Corner roundness (0..1)
        rotate: 0, // The rotation offset
        color: '#000', // #rgb or #rrggbb
        speed: 1.5, // Rounds per second
        trail: 40, // Afterglow percentage
        shadow: false, // Whether to render a shadow
        hwaccel: false, // Whether to use hardware acceleration
        className: 'spinner', // The CSS class to assign to the spinner
        zIndex: 2e9, // The z-index (defaults to 2000000000)
        top: 'auto', // Top position relative to parent in px
        left: 'auto' // Left position relative to parent in px
      };
      app.spin = new Spin(options);
      mps.subscribe('spin', _.bind(function(show) {
        if (show) {
          this.spin.spin(target);
        } else {
          this.spin.stop();
        }
      }, app));
      app.router = new Router(app);
      Backbone.history.start({pushState: true});
    },  
  };
});