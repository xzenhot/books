"use strict";

// ── Stage constants (mirror HubStage.cs) ────────────────────────────────────

const HubStage = Object.freeze({
    Parsing: "Parsing",
    Init: "Init",
    Layout: "Layout",
    Draft: "Draft",
    Published: "Published",
    Success: "Success",
    Error: "Error",
    System: "System",
    Log: "Log",
});

// ── Log level colours ────────────────────────────────────────────────────────

const LogColor = Object.freeze({
    Information: "#007bff",
    Warning: "#e67e00",
    Error: "#dc3545",
    Success: "#28a745",
    System: "#6c757d",
    Verbose: "#aaaaaa",
    Debug: "#888888",
});


let _project = {};   // last submitted ProjectSettings snapshot
let _isRunning = false;
let _startTime = null;
let _timerInterval = null;

var connection = {};


/**
 * Appends a timestamped entry to the #logs list.
 * @param {string} stage    -HubStage constant (used as label)
     * @param {string} message  -Human-readable message
         * @param {string} logLevel -LogLevel string for colour lookup
             */
const appendLog = (stage, message, logLevel = "Information") => {
    const color = LogColor[stage] ?? LogColor[logLevel] ?? "#333";
    const time = new Date().toLocaleTimeString();
    const bold = (logLevel === "Error" || logLevel === "Success") ? "font-weight:bold;" : "";

    const li = document.createElement("li");
    li.style.cssText = `color:${color};${bold}`;
    li.innerHTML = `<small style="color:#999">${time}</small> <strong>[${stage}]</strong> ${escapeHtml(message)}`;

    const list = document.getElementById("logs");
    if (!list) return;
    //list.appendChild(li);
    list.insertBefore(li, list.firstChild);  // insert before the first existing child
    // Auto-scroll to bottom
    const container = list.parentElement;
    if (container) container.scrollTop = container.scrollHeight;

};

/** Minimal HTML escaping to prevent XSS from server log messages. */
const escapeHtml = (text) =>
    String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");


$(function () {

    const connection = new signalR.HubConnectionBuilder()
        .withUrl("/agentChatHub", { withCredentials: true })
        .withAutomaticReconnect([0, 2000, 5000, 10000, 30000])
        .build();

    connection.serverTimeoutInMilliseconds = 120_000;   // 2 min — long-running pipeline
    connection.keepAliveIntervalInMilliseconds = 15_000;

    connection.onreconnecting(() => {
        appendLog(HubStage.System, "Connection lost — reconnecting...", "Warning");

    });

    connection.onreconnected(() => {
        appendLog(HubStage.System, "Reconnected.", "System");
    });

    connection.onclose(err => {
        appendLog(HubStage.System, err ? `Connection closed: ${err}` : "Connection closed.", "System");

    });

    connection.on("callback", (stage, message, logLevel) => {
        try {
            appendLog(stage, message, logLevel);
        }
        catch (err) {
            console.log(`Error processing callback: ${err}`);
        }
    });


    connection.start()
        .then(async () => {
            appendLog(HubStage.System, "Connected to hub.", "System");
        })
        .catch(err => {
            appendLog(HubStage.Error, `Connection failed: ${err}`, "Error");
        });
});