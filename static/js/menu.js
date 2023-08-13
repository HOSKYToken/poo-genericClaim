// Function to load and insert menu.html content
function loadMenu() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', 'menu.html', true);
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4 && xhr.status === 200) {
            var menuContent = xhr.responseText;
            var bodyElement = document.querySelector('body');
            bodyElement.insertAdjacentHTML('afterbegin', menuContent);
        }
    };
    xhr.send();
}

// Call the loadMenu function when the DOM is ready
document.addEventListener('DOMContentLoaded', loadMenu);
