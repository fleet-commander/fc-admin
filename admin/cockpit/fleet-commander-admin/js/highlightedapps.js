function showHighlightedApps () {
  $('#highlighted-apps-list').html('');
  $('#profile-modal').modal('hide');
  $('#highlighted-apps-modal').modal('show');
  refreshHighlightedAppsList();
}

function refreshHighlightedAppsList () {
  DEBUG > 0 && console.log('FC: Refreshing highlighted apps list');
  try {
    var changes = currentprofile.settings["org.gnome.gsettings"];
    $.each (changes, function (i,e) {
      for (key in e) {
        if (e[key] == "/org/gnome/software/popular-overrides") {
          try {
            var overrides = e['value'];
            if (Array.isArray (overrides) == false) {
              if (typeof(overrides) == 'string' &&
                overrides.match(/\[.*\]/)) {
                  var a = overrides.substring(1, overrides.length - 1);
                  if (a.length > 0) {
                    overrides = a.substring(1, a.length - 1).split("','");
                  } else {
                    overrides = null;
                  }
              } else {
                overrides = null;
              }
            } else {
                overrides = null;
            }
            $.each (overrides, function(i, app) {
              addHighlightedApp(app);
            });
            return;
          } catch (e) {}
        }
      }
    });
  } catch (e) {}
}

function addHighlightedApp(app) {
  if (typeof (app) != "string")
    return;

  if (hasSuffix (app, ".desktop") == false)
    return;

  var li = $('<li></li>', {'class': 'list-group-item', 'data-id': app, 'text': app });
  var del = $('<button></button>', {
    'class': 'pull-right btn btn-danger',
    text: 'Delete'
  });
  del.click(app, function() { deleteHighlightedApp(app); });
  del.appendTo (li);
  li.appendTo($('#highlighted-apps-list'));
}

function addHighlightedAppFromEntry () {
  clearModalFormErrors('highlighted-apps-modal');

  var app = $('#app-name').val ();

  if (hasSuffix(app, ".desktop") == false) {
    showMessageDialog(_('Application identifier must have .desktop extension'), _('Invalid entry'));
    return
  } else if (app.indexOf('"') != -1 || app.indexOf("'") != -1) {
    showMessageDialog(_('Application identifier must not contain quotes'), _('Invalid entry'));
    return
  } else if ($('#highlighted-apps-list li[data-id="' + app + '"]').length > 0) {
    showMessageDialog(_('Application identifier is already in favourites'), _('Invalid entry'));
    return
  }
  addHighlightedApp(app);
  $('#app-name').val('');
}

function deleteHighlightedApp(app) {
  $('#highlighted-apps-list li[data-id="' + app + '"]').remove();
}

function saveHighlightedAppsOld () {
  var overrides = []
  $('#highlighted-apps-list li').each(function() {
    overrides.push($(this).attr('data-id'));
  })
  fc.HighlightedApps(overrides, currentuid, function(resp){
    if (resp.status) {
      $('#highlighted-apps-modal').modal('hide');
      $('#profile-modal').modal('show');
    } else {
      showMessageDialog(_('Error saving highlighted apps'), _('Error'));
    }
  });
}

function saveHighlightedApps () {
  var overrides = []
  $('#highlighted-apps-list li').each(function() {
    overrides.push($(this).attr('data-id'));
  })

  if ("org.gnome.gsettings" in currentprofile.settings) {
    var changes = currentprofile.settings["org.gnome.gsettings"];
    var changed = false;
    $.each (changes, function (i,e) {
      for (key in e) {
        if (e[key] == "/org/gnome/software/popular-overrides") {
          e['value'] = JSON.stringify(overrides).replace(/\"/g, "\'");
          changed = true;
          break;
        }
      }
    });
    if (!changed) {
      currentprofile.settings["org.gnome.gsettings"].push({
        key: '/org/gnome/software/popular-overrides',
        value: JSON.stringify(overrides).replace(/\"/g, "\'"),
        signature: 'as'
      });
    }
  } else {
    currentprofile.settings["org.gnome.gsettings"] = [
      {
        key: '/org/gnome/software/popular-overrides',
        value: JSON.stringify(overrides).replace(/\"/g, "\'"),
        signature: 'as'
      }
    ]
  }


  $('#highlighted-apps-modal').modal('hide');
  $('#profile-modal').modal('show');
}
