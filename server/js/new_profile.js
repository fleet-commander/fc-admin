var sc;
var updater;

function updateEventList () {
  $.getJSON ("/session_changes", function (data) {
    $("#event-list").html("");
    $.each (data, function (i, item) {
      var row = item.join (" ");
      var id = data.length - 1 - i;
      var input = '<input type="checkbox" class="hidden" data-id="' + id + '"/>'
      $("#event-list").html($("#event-list").html() + "<li>" + input + row + "</li>");
    });
  });
}

function closeSession () {
  $.getJSON("/session_stop", function (data) {return;});
  sc.stop();
}

function startSpice () {
  try {
    sc = new SpiceMainConn({uri: "ws://localhost:8281/", screen_id: "spice-screen", password: "", onerror: function (e) {return;}});
  }
  catch (e) {
  }
}

function reviewChanges() {
  $("#spice-area").hide(200);
  $("#event-logs").show(200);
}

function showSession() {
  $("#spice-area").show(200);
  $("#event-logs").hide(200);
}

function createProfile() {
  closeSession();
  $('input[type="button"]').hide();
  $("input.hidden").css("display", "inline");
  window.clearInterval(updater);
  window.setTimeout(function () {
    $("input.hidden").css("display", "inline");
    reviewChanges();
  },
    1000);
}

$(document).ready (function () {
  updater = window.setInterval (updateEventList, 1000);

  $.getJSON("/session_start", function (data) {
    window.setTimeout(startSpice, 1000);
  });

  $("#event-logs").hide();
});
