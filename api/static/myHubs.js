function hubInfoAlert() {
    window.open("/about/");
}
sessionStorage.setItem('show_owned', 'true');
sessionStorage.setItem('show_shared', 'true');

// keep scroll position on refresh
document.addEventListener("DOMContentLoaded", function(event) {
    let showEdit = (sessionStorage.getItem('show_edit') === 'true');
    let showOwned = (sessionStorage.getItem('show_owned') === 'true');
    let showShared = (sessionStorage.getItem('show_shared') === 'true');

    let myHubsCheck = document.getElementById('owned-hubs');
    if (!showOwned) {

        myHubsCheck.checked = false;
    }

    let sharedHubsCheck = document.getElementById('shared-hubs');
    if (!showShared) {
        sharedHubsCheck.checked = false;
    }

    editHubs(showEdit);
    checkHubs();

    let scrollPosition = localStorage.getItem('scrollPosition');
    if (scrollPosition) window.scrollTo(0, scrollPosition);
});
window.onbeforeunload = function(e) {
    localStorage.setItem('scrollPosition', window.scrollY);
};

function checkHubs() {
    let myHubsCheck = document.getElementById('owned-hubs');
    let sharedHubsCheck = document.getElementById('shared-hubs');

    const myHubs = document.getElementsByClassName("my-hubs");
    if (myHubsCheck.checked) {
        for (let hub = 0; hub < myHubs.length; hub++) {
            myHubs[hub].style.display = "block";
            if(myHubs[hub].id === "hubs-break"){
                myHubs[hub].style.display = "inline"
            }
        }
        sessionStorage.setItem('show_owned', 'true');
    } else {
        for (let hub = 0; hub < myHubs.length; hub++) {
            myHubs[hub].style.display = "none";
        }
        sessionStorage.setItem('show_owned', 'false');
    }

    const sharedHubs = document.getElementsByClassName("shared-hubs");
    if (sharedHubsCheck.checked) {
        for (let hub = 0; hub < sharedHubs.length; hub++) {
            sharedHubs[hub].style.display = "block";
            if(sharedHubs[hub].id === "hubs-break"){
                sharedHubs[hub].style.display = "inline"
            }
        }
        sessionStorage.setItem('show_shared', 'true');
    } else {
        for (let hub = 0; hub < sharedHubs.length; hub++) {
            sharedHubs[hub].style.display = "none";
        }
        sessionStorage.setItem('show_shared', 'false');
    }
}

function editHubs(show) {
    let editElements = document.getElementsByClassName("edit-elements");

    if (show) {
        document.getElementById("stop-edit").style.display = "block";
        document.getElementById("edit").style.display = "none";

        for (let element = 0; element < editElements.length; element++) {
            editElements[element].style.display = "inline";
        }

        sessionStorage.setItem('show_edit', 'true');
        showEdit = true;
    } else {
        document.getElementById("stop-edit").style.display = "none";
        document.getElementById("edit").style.display = "block";

        for (let element = 0; element < editElements.length; element++) {
            editElements[element].style.display = "none";
        }

        sessionStorage.setItem('show_edit', 'false');
        showEdit = false;
    }
}
