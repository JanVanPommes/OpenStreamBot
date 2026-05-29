var websocket = null;
var pluginUUID = null;

// Connect to OpenStreamBot
var botSocket = null;
var isBotConnected = false;

var reconnectTimer = null;

function connectToBot() {
    if (botSocket && (botSocket.readyState === WebSocket.OPEN || botSocket.readyState === WebSocket.CONNECTING)) {
        return; // Already connected or connecting
    }

    console.log("Attempting to connect to OpenStreamBot...");
    botSocket = new WebSocket("ws://127.0.0.1:8080");

    botSocket.onopen = function() {
        console.log("Connected to OpenStreamBot!");
        isBotConnected = true;
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
        }
    };

    botSocket.onclose = function() {
        console.log("Disconnected from OpenStreamBot.");
        isBotConnected = false;
        scheduleReconnect();
    };

    botSocket.onerror = function(error) {
        console.error("OpenStreamBot WebSocket Error.");
        isBotConnected = false;
        botSocket.close();
    };
}

function scheduleReconnect() {
    if (!reconnectTimer) {
        reconnectTimer = setTimeout(function() {
            reconnectTimer = null;
            connectToBot();
        }, 5000);
    }
}

// Add a heartbeat check every 10 seconds to ensure the connection is alive
setInterval(function() {
    if (!botSocket || botSocket.readyState === WebSocket.CLOSED) {
        connectToBot();
    }
}, 10000);

// Initial connection to bot
connectToBot();

function triggerBotAction(actionName) {
    if (!botSocket || botSocket.readyState !== WebSocket.OPEN) {
        console.warn("Cannot trigger action, bot not connected (ReadyState: " + (botSocket ? botSocket.readyState : "null") + ")");
        // Force a reconnect attempt if it's dead
        connectToBot();
        return;
    }
    
    var payload = {
        event: "trigger_action_by_name",
        data: {
            action: actionName
        }
    };
    botSocket.send(JSON.stringify(payload));
}

// Elgato Stream Deck Registration
function connectElgatoStreamDeckSocket(inPort, inPluginUUID, inRegisterEvent, inInfo) {
    pluginUUID = inPluginUUID;
    websocket = new WebSocket("ws://127.0.0.1:" + inPort);

    websocket.onopen = function() {
        // Register the plugin with Stream Deck software
        var json = {
            "event": inRegisterEvent,
            "uuid": inPluginUUID
        };
        websocket.send(JSON.stringify(json));
    };

    websocket.onmessage = function (evt) {
        var jsonObj = JSON.parse(evt.data);
        var event = jsonObj['event'];
        var action = jsonObj['action'];
        var context = jsonObj['context'];

        if(event === "keyUp") {
            var payload = jsonObj['payload'];
            var settings = payload['settings'];
            
            if (settings != null && settings.hasOwnProperty('actionName')) {
                var actionName = settings['actionName'];
                console.log("Triggering OpenStreamBot action: " + actionName);
                triggerBotAction(actionName);
            } else {
                console.warn("No actionName configured for this button.");
            }
        }
    };
}
