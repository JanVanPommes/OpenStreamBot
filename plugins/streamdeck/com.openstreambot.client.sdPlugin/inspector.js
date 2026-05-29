var websocket = null;
var pluginUUID = null;
var actionInfo = {};

function connectElgatoStreamDeckSocket(inPort, inPluginUUID, inRegisterEvent, inInfo, inActionInfo) {
    pluginUUID = inPluginUUID;
    actionInfo = JSON.parse(inActionInfo);
    
    websocket = new WebSocket("ws://127.0.0.1:" + inPort);

    websocket.onopen = function() {
        var json = {
            "event": inRegisterEvent,
            "uuid": inPluginUUID
        };
        websocket.send(JSON.stringify(json));
        
        // Request existing settings
        websocket.send(JSON.stringify({
            "event": "getSettings",
            "context": pluginUUID
        }));
    };

    websocket.onmessage = function (evt) {
        var jsonObj = JSON.parse(evt.data);
        var event = jsonObj['event'];
        
        if (event === "didReceiveSettings") {
            var payload = jsonObj['payload'];
            var settings = payload['settings'];
            
            if (settings != null && settings.hasOwnProperty('actionName')) {
                document.getElementById('actionName').value = settings['actionName'];
            }
        }
    };
    
    // Listen for input changes and save settings
    document.getElementById('actionName').addEventListener('input', function(e) {
        var value = e.target.value;
        var json = {
            "event": "setSettings",
            "context": pluginUUID,
            "payload": {
                "actionName": value
            }
        };
        websocket.send(JSON.stringify(json));
    });
}
