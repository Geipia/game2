// SocketIO connection
var socket = io();

// Example: update cagnotte in real time
socket.on('update_cagnotte', function(amount) {
    document.getElementById('cagnotte').textContent = amount + ' €';
});

// Example: update player status
socket.on('player_eliminated', function(playerId) {
    var photo = document.getElementById('player_' + playerId);
    if (photo) {
        photo.classList.add('eliminated');
    }
});
