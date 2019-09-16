
var port = browser.runtime.connectNative("firefox_bookmark_logger");

var queue = [];

/*
Listen for messages from the app.
*/
port.onMessage.addListener((response) => {
    console.log("FC - Received from native app: " + response);
});

port.onDisconnect.addListener(function(data) {
    console.log("FC -Disconnected", data);
});


console.log("FC -Port for native connection to logger: ", port)

function bookmarkCreated(id, bookmark) {
    console.log('Created bookmark ' + id + ': ', bookmark);
    getBookmarkFolder(id);
    port.postMessage({'type': 'add', 'id': id, 'data': bookmark});
}

function bookmarkRemoved(id, removeinfo) {
    console.log('Removed bookmark ' + id + ': ', removeinfo);
    port.postMessage({'type': 'remove', 'id': id, 'data': removeinfo});
}

function bookmarkChanged(id, changeinfo) {
    console.log('Changed bookmark ' + id + ': ', changeinfo);
    port.postMessage({'type': 'change', 'id': id, 'data': changeinfo});
    getBookmarkFolder(id);
}

function bookmarkMoved(id, moveinfo) {
    console.log('Moved bookmark ' + id + ': ', moveinfo);
    port.postMessage({'type': 'move', 'id': id, 'data': moveinfo});
    getBookmarkFolder(id);
}

function getBookmarkFolder(id) {
    var path = '';
    var bookmark = browser.bookmarks.get(id);
    gettingBookmarks.then(onFulfilled, onRejected)
    console.log('Bookmark: ', bookmark);
    console.log('Parent: ', bookmark.parentId);
    while (bookmark.parentId) {
        console.log('Path: ', path);
        bookmark = browser.bookmarks.get(bookmark.parentId);
        path = bookmark.title + '/' + path
    }
    console.log(path)
    return path;
}

// Bookmark Event listeners
browser.bookmarks.onCreated.addListener(bookmarkCreated);
browser.bookmarks.onRemoved.addListener(bookmarkRemoved);
browser.bookmarks.onChanged.addListener(bookmarkChanged);
browser.bookmarks.onMoved.addListener(bookmarkMoved);
