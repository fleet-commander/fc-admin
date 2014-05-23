var sc;
var updater;
var changes;
var submit=false;

function updateEventList () {
  $.getJSON ("/session_changes", function (data) {
    $("#event-list").html("");
    changes = data;
    $.each (data, function (i, item) {
      var row = item.join (" ");
      var id = data.length - 1 - i;
      var input = '<input type="checkbox" class="''" data-id="' + id + '"/>'
      $("#event-list").html($("#event-list").html() + "<li>" + input + row + "</li>");
      if (submit)
      {
        $("input[data-id]").show();
      }
    });
  });
}

function startSpice () {
  try {
    sc = new SpiceMainConn({uri: "ws://localhost:8281/", screen_id: "spice-screen", password: "", onerror: function (e) {return;}});
  }
  catch (e) {
  }
  submit=false;
  updater = window.setInterval (updateEventList, 1000);
}

function closeSession () {
  $.getJSON("/session_stop", function (data) {return;});
  sc.stop();
}

function restartSession() {
  closeSession();
  showSession();
  $('input[type="button"]').show();
  $("input.hidden").css("display", "none");

  $.getJSON("/session_start", function (data) {
    window.setTimeout(startSpice, 1000);
  });
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
  submit = true;
  closeSession();
  $('input[type="button"]').hide();
  $("input.hidden").css("display", "inline");
  window.clearInterval(updater);
  window.setTimeout(function () {
    reviewChanges();
  },
   1000);
}

function deployProfile() {
  var sel = [];
  $.each($('input[data-id]:checked'), function (i,e) {
    sel.push(changes.length - 1 - $(this).attr('data-id'));
  });
  console.log(sel);
}

$(document).ready (function () {
  $.getJSON("/session_start", function (data) {
    window.setTimeout(startSpice, 1000);
  });

  $("#event-logs").hide();
});
