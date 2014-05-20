function updateEventList () {
  $.getJSON ("/session_changes", function (data) {
    $("#event-list").html("");
    $.each (data, function (i, item) {
      var row = item.join (" ");
      $("#event-list").html($("#event-list").html() + "<li>" + row + "</li>");
    });
  });
}

$(document).ready (function () {
  window.setInterval (updateEventList, 1000);

  $.getJSON("/session_start", function (data) {
    console.log(data.status);
  });
});
