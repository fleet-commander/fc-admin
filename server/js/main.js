$(document).ready (function () {
  $.getJSON ("/profiles/", function (data) {
    $.each (data, function (i, val) {
      $("#profile-list").html ($("#profile-list").html() + "<li>" + val.displayName + "</li>");
    });
  });
});
