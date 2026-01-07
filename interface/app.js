// Globale Variable für den WebSocket
let ws;
let badgeMap = {}; // Speichert alle Badges: id -> version -> url

const chatContainer = document.getElementById('chat-container');
const statusDot = document.getElementById('status');
const connectionPanel = document.getElementById('connection-panel');

// --- EINSTELLUNGEN LADEN ---
const savedFontSize = localStorage.getItem('chatFontSize') || 14;
document.documentElement.style.setProperty('--font-size', savedFontSize + 'px');
document.getElementById('font-slider').value = savedFontSize;
document.getElementById('font-val').innerText = savedFontSize + 'px';

// --- VERBINDUNGS-LOGIK ---
function connect() {
    // Falls noch eine alte Verbindung hängt, schließen
    if (ws) {
        ws.close();
    }

    ws = new WebSocket("ws://localhost:8080");

    ws.onopen = () => {
        console.log("Verbunden mit PommesBot");
        statusDot.classList.add('connected');
        connectionPanel.style.display = 'none'; // Button ausblenden
        addSystemMessage("Verbindung hergestellt.");

        // Badges anfordern
        ws.send(JSON.stringify({ action: "get_badges" }));
    };

    ws.onclose = () => {
        statusDot.classList.remove('connected');
        connectionPanel.style.display = 'block';
        addSystemMessage("Verbindung getrennt. Reconnect in 10s...");
        setTimeout(connect, 10000);
    };

    ws.onerror = (err) => {
        console.error("Socket Error:", err);
        ws.close();
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        // Hide panel if connected
        if (ws.readyState === WebSocket.OPEN) connectionPanel.style.display = 'none';

        if (data.event === "ChatMessage") {
            addChatMessage(data.data);
        } else if (data.event === "BotStatus") {
            addSystemMessage(`Status: ${data.data.status}`);
        } else if (data.event === "SystemEvent") {
            addSystemEvent(data.data);
        } else if (data.event === "BadgeMapping") {
            badgeMap = data.data;
            console.log("Badges received:", badgeMap);
        } else if (data.event === "Error") {
            addSystemMessage(`❌ FEHLER: ${data.data.message}`);
        }
    };
}

// Start: Versuche sofort beim Laden zu verbinden
connect();

// --- FUNKTIONEN ---

function addChatMessage(msgData) {
    const div = document.createElement('div');
    div.classList.add('message');

    // Zeitstempel (nur Uhrzeit)
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Farbe des Users (Fallback auf Lila, falls keine Farbe da ist)
    const userColor = msgData.color || "#a970ff";

    // Platform Style
    if (msgData.platform === 'youtube') {
        div.style.borderLeft = "3px solid #ff0000";
        div.style.backgroundColor = "rgba(255, 0, 0, 0.05)";
    }

    // Parse emotes if available
    let processedMessage = msgData.message;
    if (msgData.emotes && msgData.emotes.length > 0) {
        processedMessage = parseEmotes(msgData.message, msgData.emotes);
    } else {
        // Sanitize text if no emotes (prevent XSS)
        processedMessage = escapeHtml(msgData.message);
    }

    // Badges vorbereiten
    let badgesHtml = "";
    if (msgData.badges && Object.keys(badgeMap).length > 0) {
        badgesHtml = getBadgesHtml(msgData.badges);
    }

    // HTML zusammenbauen
    // Badge für Platform optional
    let platformIcon = "";
    if (msgData.platform === 'youtube') {
        // platformIcon = '<span style="color:red; margin-right:4px;">▶</span>'; 
    }

    div.innerHTML = `
        <span class="timestamp">${time}</span>
        <span class="badges">${badgesHtml}</span>
        <span class="username" style="color: ${userColor}">${platformIcon}${msgData.user}:</span>
        <span class="text">${processedMessage}</span>
    `;

    chatContainer.appendChild(div);
    scrollToBottom();
}

function addSystemMessage(text) {
    const div = document.createElement('div');
    div.classList.add('message');
    div.style.fontStyle = "italic";
    div.style.color = "#888";
    div.innerText = `[System] ${text}`;
    chatContainer.appendChild(div);
    scrollToBottom();
}

function addSystemEvent(eventData) {
    const div = document.createElement('div');
    div.classList.add('message');
    div.classList.add('system-event'); // Für CSS Styling

    // Style direkt hier oder besser in CSS ausgelagert
    div.style.borderLeft = "4px solid #a970ff";
    div.style.backgroundColor = "rgba(169, 112, 255, 0.1)";
    div.style.padding = "10px";
    div.style.marginTop = "5px";
    div.style.marginBottom = "5px";

    div.innerHTML = `
        <div style="font-weight: bold; color: #a970ff; margin-bottom: 2px;">${eventData.type.toUpperCase()}</div>
        <div style="color: white;">${eventData.message}</div>
    `;

    chatContainer.appendChild(div);
    scrollToBottom();
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// --- SETTINGS UI LOGIC ---
function toggleSettings() {
    document.getElementById('settings-panel').classList.toggle('open');
}

// Schriftgröße ändern & speichern
document.getElementById('font-slider').addEventListener('input', (e) => {
    const size = e.target.value;
    document.documentElement.style.setProperty('--font-size', size + 'px');
    document.getElementById('font-val').innerText = size + 'px';
    localStorage.setItem('chatFontSize', size);
});

// --- CHAT SENDING ---
const chatInput = document.getElementById('chat-input');

chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: "send_chat",
            message: text
        }));
        chatInput.value = "";
    } else {
        addSystemMessage("Fehler: Nicht verbunden!");
    }
}

function startYouTubeStream() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: "youtube_stream_start" }));
        addSystemMessage("YouTube Stream-Suche angefordert...");
    } else {
        addSystemMessage("Fehler: Nicht verbunden!");
    }
}

// --- HELPER FUNCTIONS ---

function getBadgesHtml(badges) {
    let html = "";
    for (let badge of badges) {
        // badge has {id: "broadcaster", version: "1"}
        if (badgeMap[badge.id] && badgeMap[badge.id][badge.version]) {
            const url = badgeMap[badge.id][badge.version];
            html += `<img src="${url}" class="chat-badge" style="vertical-align: middle; margin-right: 4px; height: 1em;">`;
        }
    }
    return html;
}

function parseEmotes(text, emotes) {
    // 1. Sort emotes by start index to handle them in order
    emotes.sort((a, b) => a.start - b.start);

    let result = "";
    let currentIndex = 0;

    for (let emote of emotes) {
        // Add text before the emote (escaped)
        if (emote.start > currentIndex) {
            result += escapeHtml(text.substring(currentIndex, emote.start));
        }

        // Add the emote image
        const url = `https://static-cdn.jtvnw.net/emoticons/v2/${emote.id}/default/dark/1.0`;
        // Twitch text range is inclusive
        const code = text.substring(emote.start, emote.end + 1);
        result += `<img src="${url}" alt="${code}" title="${code}" class="chat-emote" style="vertical-align: middle; height: 1.2em;">`;

        currentIndex = emote.end + 1;
    }

    // Add remaining text
    if (currentIndex < text.length) {
        result += escapeHtml(text.substring(currentIndex));
    }

    return result;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function (m) { return map[m]; });
}
