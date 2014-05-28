var uid = "";

function populateUsersGroups(users, groups) {
  $.each(users, function (i,e) {
    console.log("bar");
    $("#profile-users").html($("#profile-users").html() + '<option value="' + e +'">' + e + '</value>');
  });
  $.each(groups, function(i,e) {
    console.log("foo");
    $("#profile-groups").html($("#profile-groups").html() + '<option value="' + e +'">' + e + '</value>');
  });
}

function profileSave() {
  $.post("/profile_save/" + uid, $('form').serialize(), function (data) {
    //location.pathname = "/";
    console.log(data);
  });
}

$(document).ready (function () {
  var path = location.pathname.split("/");
  uid = path[path.length - 1];
  $.getJSON("/getent", function (data) {
    populateUsersGroups(data.users, data.groups);
  });
});
