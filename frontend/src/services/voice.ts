/**
 * Voice AI WebCall Service
 * Handles API calls to backend, microphone access, and WebRTC call state management.
 */

export type CallState =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'listening'
  | 'processing'
  | 'speaking'
  | 'ending'
  | 'disconnected'
  | 'error';

export interface TranscriptItem {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: string;
}

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export class VoiceCallService {
  private sessionId: string | null = null;
  private mediaStream: MediaStream | null = null;
  private peerConnection: RTCPeerConnection | null = null;
  private audioElement: HTMLAudioElement | null = null;

  public onStateUpdate?: (state: CallState) => void;
  public onTranscriptUpdate?: (item: TranscriptItem) => void;

  constructor() {
    // Persistent HTMLAudioElement for remote AI audio playback
    if (typeof window !== 'undefined') {
      this.audioElement = new Audio();
      this.audioElement.autoplay = true;
    }
  }

  /**
   * Requests browser microphone permission and verifies live track status.
   */
  async requestMicrophone(): Promise<MediaStream> {
    console.log('[MIC] Requesting microphone');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
          sampleRate: 16000,
        },
      });
      console.log('[MIC] Permission granted');
      
      const audioTrack = stream.getAudioTracks()[0];
      if (audioTrack) {
        console.log(`[MIC] Audio track created (enabled: ${audioTrack.enabled}, state: ${audioTrack.readyState})`);
      }
      
      this.mediaStream = stream;
      return stream;
    } catch (error) {
      console.error('[MIC][ERROR] Microphone access failed:', error);
      throw new Error('Unable to access microphone. Please allow microphone access in browser permissions.');
    }
  }

  /**
   * Connects local browser WebRTC peer connection with backend via SDP offer/answer.
   */
  async connectWebRTC(sessionId: string): Promise<void> {
    console.log('[WEBRTC] Creating peer connection');
    const pc = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
    });
    this.peerConnection = pc;

    // Track WebRTC connection states
    pc.onconnectionstatechange = () => {
      console.log(`[WEBRTC] Connection state: ${pc.connectionState}`);
      if (pc.connectionState === 'connected') {
        this.onStateUpdate?.('connected');
        setTimeout(() => this.onStateUpdate?.('listening'), 800);
      } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
        this.onStateUpdate?.('disconnected');
      }
    };

    // Attach local microphone audio track to peer connection
    if (this.mediaStream) {
      this.mediaStream.getAudioTracks().forEach((track) => {
        pc.addTrack(track, this.mediaStream!);
        console.log('[MIC] Audio track added to PeerConnection');
      });
    }

    // Persistent audio element handles incoming WebRTC audio track from AI assistant
    pc.ontrack = (event) => {
      console.log('[AUDIO] Remote audio track received from WebRTC');
      if (this.audioElement) {
        this.audioElement.srcObject = event.streams[0];
        this.audioElement.play().catch((err) => {
          console.error('[Audio] Playback failed (autoplay restriction may require interaction):', err);
        });
      }
    };

    // Create DataChannel for real-time transcript & state messages
    const dc = pc.createDataChannel('pipecat');
    this.setupDataChannel(dc);

    pc.ondatachannel = (event) => {
      this.setupDataChannel(event.channel);
    };

    // Create WebRTC SDP offer
    console.log('[WEBRTC] Creating offer');
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    console.log('[WEBRTC] Local description set');

    console.log('[WEBRTC] Sending offer to backend');
    const response = await fetch(`${BACKEND_URL}/api/webrtc/offer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sdp: offer.sdp,
        type: offer.type,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[WEBRTC][ERROR] SDP offer failed:', errorText);
      throw new Error(`WebRTC SDP negotiation failed (${response.status}): ${errorText}`);
    }

    const answer = await response.json();
    console.log('[WEBRTC] Answer received');
    await pc.setRemoteDescription(new RTCSessionDescription({
      type: answer.type,
      sdp: answer.sdp,
    }));
    console.log('[WEBRTC] Remote description set');
  }

  private setupDataChannel(channel: RTCDataChannel) {
    channel.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'state' && data.state) {
          this.onStateUpdate?.(data.state as CallState);
        } else if (data.type === 'transcript' && data.text) {
          this.onTranscriptUpdate?.({
            id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
            sender: data.sender || 'ai',
            text: data.text,
            timestamp: data.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          });
        }
      } catch (e) {
        console.log('[DATACHANNEL] Received raw message:', event.data);
      }
    };
  }

  /**
   * Starts a new WebCall session with backend and connects WebRTC audio stream.
   */
  async startCall(): Promise<{ sessionId: string }> {
    try {
      this.onStateUpdate?.('connecting');

      // 1. Request microphone permission
      await this.requestMicrophone();

      // 2. Obtain session ID from backend
      console.log('[SESSION] Requesting new session ID from backend');
      const response = await fetch(`${BACKEND_URL}/api/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[SESSION][ERROR] Backend start call error:', response.status, errorText);
        throw new Error(`Backend service error (${response.status}): ${errorText}`);
      }

      const data = await response.json();
      this.sessionId = data.session_id;
      console.log(`[SESSION] Initialized session '${this.sessionId}'`);

      // 3. Establish WebRTC connection and attach Pipecat pipeline
      await this.connectWebRTC(this.sessionId!);

      return { sessionId: this.sessionId! };
    } catch (err: any) {
      console.error('[SESSION][ERROR] startCall exception:', err);
      this.onStateUpdate?.('error');
      throw err;
    }
  }

  /**
   * Ends current call session and cleans up microphone and peer connections.
   */
  async endCall(): Promise<void> {
    this.onStateUpdate?.('ending');

    if (this.sessionId) {
      try {
        await fetch(`${BACKEND_URL}/api/stop`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: this.sessionId }),
        });
        console.log(`[SESSION] Sent stop request for session '${this.sessionId}'`);
      } catch (err) {
        console.warn('[SESSION] Error sending stop request to backend:', err);
      }
    }

    // Stop microphone tracks
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
      console.log('[MIC] Microphone tracks stopped');
    }

    // Close peer connection
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
      console.log('[WEBRTC] Peer connection closed');
    }

    this.sessionId = null;
    this.onStateUpdate?.('disconnected');
    setTimeout(() => this.onStateUpdate?.('idle'), 500);
  }

  getSessionId(): string | null {
    return this.sessionId;
  }
}

export const voiceService = new VoiceCallService();
