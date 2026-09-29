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
  private remoteAudio: HTMLAudioElement | null = null;

  public onStateUpdate?: (state: CallState) => void;
  public onTranscriptUpdate?: (item: TranscriptItem) => void;

  constructor() {
    if (typeof window !== 'undefined') {
      this.remoteAudio = new Audio();
      this.remoteAudio.autoplay = true;
      // @ts-ignore
      this.remoteAudio.playsInline = true;
    }
  }

  /**
   * Requests browser microphone permission and verifies track settings.
   */
  async requestMicrophone(): Promise<MediaStream> {
    console.log('[MIC] Requesting microphone');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      console.log('[MIC] Permission granted');

      const audioTrack = stream.getAudioTracks()[0];
      if (audioTrack) {
        console.log('[MIC] Track settings:', audioTrack.getSettings());
        console.log(`[MIC] Track status - enabled: ${audioTrack.enabled}, readyState: ${audioTrack.readyState}`);
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

    // Log WebRTC State Changes
    pc.onconnectionstatechange = () => {
      console.log('[WEBRTC] connectionState:', pc.connectionState);
      if (pc.connectionState === 'connected') {
        this.onStateUpdate?.('connected');
        setTimeout(() => this.onStateUpdate?.('listening'), 500);
      } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
        this.onStateUpdate?.('disconnected');
      }
    };

    pc.oniceconnectionstatechange = () => {
      console.log('[WEBRTC] iceConnectionState:', pc.iceConnectionState);
    };

    pc.onicegatheringstatechange = () => {
      console.log('[WEBRTC] iceGatheringState:', pc.iceGatheringState);
    };

    pc.onsignalingstatechange = () => {
      console.log('[WEBRTC] signalingState:', pc.signalingState);
    };

    // 1. Add microphone tracks before creating offer
    if (this.mediaStream) {
      this.mediaStream.getAudioTracks().forEach((track) => {
        pc.addTrack(track, this.mediaStream!);
        console.log('[MIC] Audio track added to PeerConnection');
      });
    }

    // 2. Attach persistent HTMLAudioElement for incoming remote audio track
    pc.ontrack = async (event) => {
      console.log('[AUDIO] Remote track:', event.track.kind);
      const stream = event.streams[0] || new MediaStream([event.track]);
      if (this.remoteAudio) {
        this.remoteAudio.srcObject = stream;
        try {
          await this.remoteAudio.play();
          console.log('[AUDIO] Remote audio track active');
        } catch (error) {
          console.error('[AUDIO] Playback failed:', error);
        }
      }
    };

    // 3. Create DataChannel for transcript & state sync
    const dc = pc.createDataChannel('pipecat');
    this.setupDataChannel(dc);

    pc.ondatachannel = (event) => {
      this.setupDataChannel(event.channel);
    };

    // 4. Create SDP offer
    console.log('[WEBRTC] Creating offer');
    const offer = await pc.createOffer();
    console.log('[WEBRTC] Local description set');
    await pc.setLocalDescription(offer);

    const offerHasAudio = offer.sdp?.includes('m=audio') ?? false;
    console.log(`[WEBRTC] Offer contains audio: ${offerHasAudio}`);

    // 5. Send SDP offer to backend
    console.log('[WEBRTC] Sending offer');
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

    const answerHasAudio = answer.sdp?.includes('m=audio') ?? false;
    console.log(`[WEBRTC] Answer contains audio: ${answerHasAudio}`);

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
        console.log('[DATACHANNEL] Raw message:', event.data);
      }
    };
  }

  /**
   * Starts a new WebCall session with backend and connects WebRTC audio stream.
   */
  async startCall(): Promise<{ sessionId: string }> {
    try {
      this.onStateUpdate?.('connecting');

      // 1. Request microphone permission & get track
      await this.requestMicrophone();

      // 2. Obtain session ID from backend
      console.log('[SESSION] Requesting session ID from backend');
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
      console.log(`[SESSION] Session ID: ${this.sessionId}`);

      // 3. Establish WebRTC connection and attach Pipecat pipeline
      try {
        await this.connectWebRTC(this.sessionId!);
      } catch (error) {
        console.error('[WEBRTC] Connection failed:', error);
        await this.endCall();
        throw error;
      }

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
