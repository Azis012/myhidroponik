const { 
    default: makeWASocket, 
    useMultiFileAuthState, 
    DisconnectReason 
} = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const pino = require('pino');
const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const PORT = process.env.PORT || 3000;
let sock = null;

// Initialize Baileys connection
async function connectToWhatsApp() {
    const authDir = path.join(__dirname, 'auth_info_baileys');
    const { state, saveCreds } = await useMultiFileAuthState(authDir);

    console.log("[WA Gateway] Starting WhatsApp socket connection...");

    sock = makeWASocket({
        auth: state,
        printQRInTerminal: false, // We will print it manually for control
        logger: pino({ level: 'silent' }), // Hide verbose logger
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log("\n=================== SCAN QR CODE DENGAN WHATSAPP ===================");
            qrcode.generate(qr, { small: true });
            console.log("===================================================================\n");
        }

        if (connection === 'close') {
            const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log('[WA Gateway] Connection closed due to: ', lastDisconnect?.error || 'unknown');
            if (shouldReconnect) {
                console.log('[WA Gateway] Reconnecting...');
                connectToWhatsApp();
            } else {
                console.log('[WA Gateway] Connection lost. Logged out. Delete auth_info_baileys folder and restart.');
            }
        } else if (connection === 'open') {
            console.log('[WA Gateway] SUCCESS! WhatsApp connected successfully.');
        }
    });
}

// Helper to check if socket is connected
function isConnected() {
    return sock && sock.user;
}

// POST Endpoint to send a message
app.post('/send', async (req, res) => {
    let { number, message } = req.body;

    if (!number || !message) {
        return res.status(400).json({ 
            status: false, 
            message: "Missing 'number' or 'message' parameter." 
        });
    }

    if (!isConnected()) {
        return res.status(503).json({ 
            status: false, 
            message: "WhatsApp Gateway is not connected. Scan the QR code first." 
        });
    }

    try {
        // Normalize number: remove non-digit characters
        let cleanNumber = number.replace(/\D/g, '');
        
        // Handle local Indonesian number format
        if (cleanNumber.startsWith('0')) {
            cleanNumber = '62' + cleanNumber.slice(1);
        }
        
        // Add WhatsApp suffix if not present
        if (!cleanNumber.endsWith('@s.whatsapp.net')) {
            cleanNumber = cleanNumber + '@s.whatsapp.net';
        }

        console.log(`[WA Gateway] Attempting to send message to ${cleanNumber}...`);
        
        // Send message
        const sentMsg = await sock.sendMessage(cleanNumber, { text: message });

        return res.status(200).json({ 
            status: true, 
            message: "Message sent successfully.",
            data: sentMsg 
        });
    } catch (error) {
        console.error("[WA Gateway] Failed to send message:", error);
        return res.status(500).json({ 
            status: false, 
            message: "Failed to send message.",
            error: error.message 
        });
    }
});

// GET status endpoint
app.get('/status', (req, res) => {
    if (isConnected()) {
        res.json({ status: true, message: "Connected", user: sock.user });
    } else {
        res.json({ status: false, message: "Disconnected. Please check QR code terminal." });
    }
});

// Start WhatsApp socket
connectToWhatsApp();

// Start Express server
app.listen(PORT, () => {
    console.log(`[WA Gateway API] Server running on http://localhost:${PORT}`);
});
