var sc;

function updateEventList () {
  $.getJSON ("/session_changes", function (data) {
    $("#event-list").html("");
    $.each (data, function (i, item) {
      var row = item.join (" ");
      $("#event-list").html($("#event-list").html() + "<li>" + row + "</li>");
    });
  });
}

function closeSession () {
  $.getJSON("/session_stop", function (data) {return;});
}

function startSpice () {
  try {
    sc = new SpiceMainConn({uri: "ws://localhost:8281/", screen_id: "spice-screen", password: "", onerror: function (e) {return;}});
  }
  catch (e) {
  }
}

$(document).ready (function () {
  window.setInterval (updateEventList, 1000);

  $.getJSON("/session_start", function (data) {
    window.setTimeout(startSpice, 1000);
  });
});
