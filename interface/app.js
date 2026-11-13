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

let reconnectTimer = null;

// --- VERBINDUNGS-LOGIK ---
function connect() {
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    // Falls noch eine alte Verbindung hängt, sauber schließen ohne Event-Kaskade
    if (ws) {
        try {
            ws.onclose = null;
            ws.onerror = null;
            ws.close();
        } catch (e) {}
    }

    const host = window.location.hostname || "localhost";
    ws = new WebSocket(`ws://${host}:8080`);

    ws.onopen = () => {
        console.log("Verbunden mit PommesBot");
        statusDot.classList.add('connected');
        connectionPanel.style.display = 'none'; // Button ausblenden
        addSystemMessage("Verbindung hergestellt.");

        // Badges & Queue-Status anfordern
        ws.send(JSON.stringify({ action: "get_badges" }));
        ws.send(JSON.stringify({ event: "get_queue_status" }));
    };

    ws.onclose = () => {
        statusDot.classList.remove('connected');
        connectionPanel.style.display = 'block';
        addSystemMessage("Verbindung getrennt. Reconnect in 3s...");
        if (!reconnectTimer) {
            reconnectTimer = setTimeout(connect, 3000);
        }
    };

    ws.onerror = (err) => {
        console.error("Socket Error:", err);
        try { ws.close(); } catch (e) {}
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        // Hide panel if connected
        if (ws.readyState === WebSocket.OPEN) connectionPanel.style.display = 'none';

        if (data.event === "ChatMessage") {
            addChatMessage(data.data);
        } else if (data.event === "BotStatus") {
            addSystemMessage(`Status: ${data.data.status}`);
        } else if (data.event === "QueueStatus") {
            updateQueueStatusBadge(data.data);
        } else if (data.event === "SystemEvent") {
            if (data.data.type === "twitch_first_message" || data.data.type === "youtube_first_message") {
                return; // Ignoriert für Chat-Ansicht, da ChatMessage markiert wird
            }
            addSystemEvent(data.data);
        } else if (data.event === "BadgeMapping") {
            badgeMap = data.data;
            console.log("Badges received:", badgeMap);
        } else if (data.event === "Error") {
            addSystemMessage(`❌ FEHLER: ${data.data.message}`);
        }
    };
}

let latestQueueStatuses = {};
function updateQueueStatusBadge(statuses) {
    if (statuses && typeof statuses === 'object') {
        latestQueueStatuses = statuses;
    }
    const badge = document.getElementById('queue-status-badge');
    if (!badge) return;

    const nowSec = Date.now() / 1000;
    const pausedList = [];
    for (const [qName, qData] of Object.entries(latestQueueStatuses)) {
        if (qData && (qData.paused || qData.status === "Paused")) {
            let label = qName;
            if (qData.paused_until) {
                const rem = Math.max(0, Math.round(qData.paused_until - nowSec));
                if (rem > 0) {
                    const remStr = rem >= 60 ? `${Math.floor(rem / 60)}m ${String(rem % 60).padStart(2, '0')}s` : `${rem}s`;
                    label += ` (${remStr})`;
                }
            }
            if (qData.pending && qData.pending > 0) {
                label += ` [+${qData.pending}]`;
            }
            pausedList.push(label);
        }
    }

    if (pausedList.length > 0) {
        badge.style.display = 'inline-block';
        badge.innerText = `⏸ Queue Pausiert: ${pausedList.join(', ')}`;
    } else {
        badge.style.display = 'none';
        badge.innerText = '';
    }
}
setInterval(() => updateQueueStatusBadge(null), 1000);

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
        const isEmoteOnly = msgData.emote_only === true;
        if (isEmoteOnly) {
            div.classList.add('emote-only');
        }
        processedMessage = parseEmotes(msgData.message, msgData.emotes, isEmoteOnly);
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

    let firstMessageBadge = "";
    if (msgData.is_first_message) {
        firstMessageBadge = `<span style="background-color: #ffd700; color: #000; padding: 2px 4px; border-radius: 4px; font-size: 0.8em; margin-right: 5px; font-weight: bold;" title="Erste Nachricht heute">FIRST</span>`;
    }

    div.innerHTML = `
        <span class="timestamp">${time}</span>
        <span class="badges">${badgesHtml}</span>
        ${firstMessageBadge}
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

function triggerTestShort() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            event: "trigger_action_by_name",
            data: { action: "Shorts Timer" }
        }));
        addSystemMessage("📱 YouTube Short Wiedergabe angefordert...");
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

function parseEmotes(text, emotes, isEmoteOnly = false) {
    // 1. Sort emotes by start index to handle them in order
    emotes.sort((a, b) => a.start - b.start);

    // Use animated format (works for both animated and static emotes)
    // Scale: 2.0 for inline, 2.0 for emote-only (same resolution, CSS controls display size)
    const scale = '2.0';
    const emoteClass = isEmoteOnly ? 'chat-emote emote-only-size' : 'chat-emote';

    let result = "";
    let currentIndex = 0;

    for (let emote of emotes) {
        // Add text before the emote (escaped)
        if (emote.start > currentIndex) {
            result += escapeHtml(text.substring(currentIndex, emote.start));
        }

        // Add the emote image (animated format with fallback to default)
        const url = `https://static-cdn.jtvnw.net/emoticons/v2/${emote.id}/animated/dark/${scale}`;
        const fallbackUrl = `https://static-cdn.jtvnw.net/emoticons/v2/${emote.id}/default/dark/${scale}`;
        // Twitch text range is inclusive
        const code = text.substring(emote.start, emote.end + 1);
        result += `<img src="${url}" alt="${code}" title="${code}" class="${emoteClass}" onerror="this.src='${fallbackUrl}';this.onerror=null;">`;

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
