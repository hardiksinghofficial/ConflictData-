import { useEffect, useRef, useState } from 'react';
import API_BASE from '../config';

const useTacticalWS = (onMessage) => {
    const ws = useRef(null);
    const [status, setStatus] = useState('OFFLINE');
    const reconnectTimer = useRef(null);

    const connect = () => {
        if (ws.current) return;

        // Convert HTTP(S) API_BASE to WS(S)
        let wsUrl;
        if (API_BASE.startsWith('http')) {
            wsUrl = API_BASE.replace('http', 'ws') + '/api/v1/ws';
        } else {
            // Relative mode
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            wsUrl = `${protocol}//${window.location.host}/api/v1/ws`;
        }

        console.log(`[WS] Connecting to ${wsUrl}...`);
        ws.current = new WebSocket(wsUrl);

        ws.current.onopen = () => {
            console.log('[WS] Connection ESTABLISHED');
            setStatus('ONLINE');
            if (reconnectTimer.current) {
                clearTimeout(reconnectTimer.current);
                reconnectTimer.current = null;
            }
        };

        ws.current.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (onMessage) onMessage(data);
            } catch (err) {
                console.error('[WS] Parse Error:', err);
            }
        };

        ws.current.onclose = () => {
            console.log('[WS] Connection CLOSED');
            setStatus('OFFLINE');
            ws.current = null;
            // Reconnect logic
            reconnectTimer.current = setTimeout(connect, 5000);
        };

        ws.current.onerror = (err) => {
            console.error('[WS] Error:', err);
            ws.current.close();
        };
    };

    useEffect(() => {
        connect();
        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, []);

    return { status };
};

export default useTacticalWS;
