//Defaults the show_owned and show_shared check items to true on first page load.
sessionStorage.setItem('show_owned', 'true');
sessionStorage.setItem('show_shared', 'true');


/**
 * Handles refreshes of myHubs page
 */
document.addEventListener("DOMContentLoaded", function(event) {

    // check session to see if edit hubs button selected, or show owned/shared hubs filters are checked
    let showEdit = (sessionStorage.getItem('show_edit') === 'true');
    let showOwned = (sessionStorage.getItem('show_owned') === 'true');
    let showShared = (sessionStorage.getItem('show_shared') === 'true');
    let scrollPosition = localStorage.getItem('scrollPosition');

    // access filter check boxes and uncheck them visually if unchecked before refresh
    let myHubsCheck = document.getElementById('owned-hubs');
    if (!showOwned) {
        myHubsCheck.checked = false;
    }
    let sharedHubsCheck = document.getElementById('shared-hubs');
    if (!showShared) {
        sharedHubsCheck.checked = false;
    }

    // based on session storage call edit hubs to show are not show hub editing UI features
    editHubs(showEdit);

    // same as edit hubs but hides or un-hides hubs based on filter checks
    checkHubs();

    // resets scroll position if a previous storage item found
    if (scrollPosition) window.scrollTo(0, scrollPosition);
});

/**
 * Saves current scroll position before refresh
 */
window.onbeforeunload = function(e) {
    localStorage.setItem('scrollPosition', window.scrollY);
};

/**
 * Changes the visibility of a hub depending on the checkbox
 */
function checkHubs() {

    // gets the current status of the checkboxes owned-hubs and shared-hubs to determine visibility
    let myHubsCheck = document.getElementById('owned-hubs');
    let sharedHubsCheck = document.getElementById('shared-hubs');

    // gets all hubs on my hubs page
    const myHubs = document.getElementsByClassName("my-hubs");
    const sharedHubs = document.getElementsByClassName("shared-hubs");

    // handles visibility of hubs
    changeVisibility(myHubsCheck, myHubs)
    changeVisibility(sharedHubsCheck, sharedHubs)
}

/**
 * Handles the visibility of hubs depending on the filter checked for the class of the hub. (Owned or Shared)
 *
 * @param check - checkbox relating to the type of hub
 * @param hubs - collection of hubs of a certain class type (owned or shared)
 */
function changeVisibility(check, hubs) {

    // if filter checked then show hubs
    if (check.checked) {
        for (let hub = 0; hub < hubs.length; hub++) {
            hubs[hub].style.display = "block";
            if(hubs[hub].id === "hubs-break"){
                hubs[hub].style.display = "inline"
            }
        }

        // set session check to retain filter on refresh
        sessionStorage.setItem('show_owned', 'true');
    }

    // if filter unchecked hide hubs
    else {
        for (let hub = 0; hub < hubs.length; hub++) {
            hubs[hub].style.display = "none";
        }

        // set session check to retain filter on refresh
        sessionStorage.setItem('show_owned', 'false');
    }
}

/**
 * Determines whether elements relating to hub editing are shown or not depending on param value
 *
 * @param show - boolean value determining whether editing elements are shown (True - shown, False - hidden).
 */
function editHubs(show) {

    // gets all the editing elements (including add user form, delete buttons, etc.)
    let editElements = document.getElementsByClassName("edit-elements");

    // show editing elements
    if (show) {
        document.getElementById("stop-edit").style.display = "block";
        document.getElementById("edit").style.display = "none";

        for (let element = 0; element < editElements.length; element++) {
            editElements[element].style.display = "inline";
        }

        // store option of showing editing elements
        sessionStorage.setItem('show_edit', 'true');
    }

    // hide editing elements
    else {
        document.getElementById("stop-edit").style.display = "none";
        document.getElementById("edit").style.display = "block";

        for (let element = 0; element < editElements.length; element++) {
            editElements[element].style.display = "none";
        }

        // store option of hiding editing elements
        sessionStorage.setItem('show_edit', 'false');
    }

}
