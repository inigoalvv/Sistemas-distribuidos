var socket = io.connect('http://' + window.location.hostname + ':' + location.port);
var userLabels = {};

document.querySelectorAll('.spreadsheet td').forEach(function(cell) {
    cell.addEventListener('input', function() {
        var id = cell.id;
        var text = cell.textContent;
        var label = getLabelPosition(cell);
        socket.emit('update_cell', { id: id, text: text, label: label, user: currentUser });
    });
});

socket.on('update_cell', (data) => {
    const { id, text, label, user } = data;
    var cell = document.getElementById(id);
    if (cell) {
        cell.textContent = text;
        if (user !== currentUser) {
            updateUserLabel(user, cell);
        }
    }
});

function getLabelPosition(element) {
    var selection = window.getSelection();
    if (selection.rangeCount > 0) {
        var range = selection.getRangeAt(0);
        var preLabelRange = range.cloneRange();
        preLabelRange.selectNodeContents(element);
        preLabelRange.setEnd(range.endContainer, range.endOffset);
        return preLabelRange.toString().length;
    }
    return 0;
}

function updateUserLabel(user, cell) {
    let userLabel = userLabels[user];
    if (!userLabel) {
        userLabel = document.createElement('div');
        userLabel.className = 'user-label';
        userLabel.innerText = user;
        document.querySelector('.spreadsheet-container').appendChild(userLabel);
        userLabels[user] = userLabel;
    }

    const rect = cell.getBoundingClientRect();
    const cellLeft = rect.left;
    const cellTop = rect.top;
    
    userLabel.style.top = `${cellTop - 20}px`;
    userLabel.style.left = `${cellLeft}px`;
}

function saveChanges() {
    var data = [];
    var rows = document.querySelectorAll('.spreadsheet tr');
    rows.forEach(function(row) {
        var rowData = [];
        var cells = row.querySelectorAll('td');
        cells.forEach(function(cell) {
            rowData.push(cell.innerText);
        });
        data.push(rowData);
    });

    fetch('/spreadsheet', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ data: data })
    })
    .then(response => {
        if (response.ok) {
            return response.text();
        }
        throw new Error('An error occurred while saving the data');
    })
    .then(message => {
        alert(message);
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while saving the data');
    });
}

const currentUser = '{{ current_user.username }}';
