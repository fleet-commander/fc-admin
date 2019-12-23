
/***************************************************
 Native port connection
***************************************************/

var port = browser.runtime.connectNative("firefox_bookmark_fclogger");

port.onMessage.addListener((response) => {
    console.log("FC - Received from native app: " + response);
});

port.onDisconnect.addListener(function(data) {
    console.log("FC -Disconnected", data);
});

/**************************************************
 Helpers
**************************************************/

// Communicate bookmarks to native script
function sendBookmark(bookmark) {
    if (bookmark.folder == '') bookmark.folder = null;
    console.log(`Submitting bookmark to logger: ${bookmark}`, bookmark)
    port.postMessage(bookmark);
}

// Get bookmark information
function getBookmarkData(action, id, bookmark_info) {

    var bookmark_object = {
        action: action,
        id: id,
        title: null,
        url: null,
        folder: null,
        placement: 'menu' // By default, we place bookmarks in menu
    };

    // Promise reject method
    function onRejected(error) {
        console.log(`Unable to get bookmark data: ${error}`);
    };

    // Promise fullfill method
    function onFulfilled(bookmark_data) {
        var bookmark = bookmark_data[0];
        
        // Setup initial data if not already set
        if (!this.title) this.title = bookmark.title;
        if (!this.url) this.url = bookmark.url;

        // If this bookmark has a parent we need to iterate
        console.log("PARENT: ", bookmark.parentId)
        if (bookmark.parentId && bookmark.parentId != 'root________') {
            if (bookmark.parentId == 'toolbar_____') this.placement = 'toolbar';
            if (this.folder == null) {
                // This is the bookmark title, not the folder
                this.folder = '';
            } else {
                this.folder =  bookmark.title + '/' + this.folder
            }
            var bookmark_promise = browser.bookmarks.get(bookmark.parentId);
            bookmark_promise.then(
                onFulfilled.bind(this),
                onRejected.bind(this))
        } else {
            // We reached bookmarks root. Submit this bookmark information.
            console.log(`Bookmark information: ${this}`, this)
            sendBookmark(this);
        }
    }
    
    // Initiate promise chain to get bookmark folder info
    var bookmark_promise = browser.bookmarks.get(bookmark_object.id);
    bookmark_promise.then(
        onFulfilled.bind(bookmark_object),
        onRejected.bind(bookmark_object))
}


/***************************************************
 Bookmark Event listeners
***************************************************/

function bookmarkCreated(id, bookmark_info) {
    console.log('Created bookmark ' + id + ': ', bookmark_info);
    getBookmarkData('add', id, bookmark_info);
}

function bookmarkRemoved(id, bookmark_info) {
    console.log('Created bookmark ' + id + ': ', bookmark_info);
    var bmark = {
        action: 'remove',
        id: id,
    };
    sendBookmark(bmark);
}

function bookmarkChanged(id, bookmark_info) {
    console.log('Changed bookmark ' + id + ': ', bookmark_info);
    getBookmarkData('change', id, bookmark_info);
}

function bookmarkMoved(id, bookmark_info) {
    console.log('Moved bookmark ' + id + ': ', bookmark_info);
    getBookmarkData('move', id, bookmark_info);
}

// Initialize listeners
browser.bookmarks.onCreated.addListener(bookmarkCreated);
browser.bookmarks.onRemoved.addListener(bookmarkRemoved);
browser.bookmarks.onChanged.addListener(bookmarkChanged);
browser.bookmarks.onMoved.addListener(bookmarkMoved);
