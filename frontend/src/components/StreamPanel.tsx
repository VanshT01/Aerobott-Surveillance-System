import { useEffect, useRef, useState } from "react";
import { api, liveUrl } from "../lib/api";
import type { Device } from "../types";

interface Props {
  selectedDevice: Device | null;
  onDeviceChanged: () => Promise<void>;
}

export function StreamPanel({ selectedDevice, onDeviceChanged }: Props) {
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [message, setMessage] = useState("Select a camera to view the stream.");
  const [messageType, setMessageType] = useState<"info" | "error">("info");
  const [pc, setPc] = useState<RTCPeerConnection | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    setStreamUrl(null);
    setMessage(selectedDevice?.device_type === "camera" ? "Stream not loaded." : "Select a camera to view the stream.");
    setMessageType("info");

    if (pc) {
      pc.close();
      setPc(null);
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, [selectedDevice?.id]);

  async function refreshStream() {
    setStreamUrl(null);

    if (!selectedDevice || selectedDevice.device_type !== "camera") {
      setMessage("Select a camera device to view a stream.");
      setMessageType("error");
      return;
    }

    if (!selectedDevice.rtsp_url?.trim()) {
      setMessage("This camera does not have an RTSP URL.");
      setMessageType("error");
      return;
    }

    setMessage("Checking camera stream...");
    setMessageType("info");

    try {
      const checked = await api.checkStream(selectedDevice.id);

      if (checked.status !== "online") {
        setMessage("Stream unavailable. The RTSP URL could not be opened.");
        setMessageType("error");
        await onDeviceChanged();
        return;
      }

      setMessage("");
      setStreamUrl(liveUrl(selectedDevice.id));
      await onDeviceChanged();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Stream check failed.");
      setMessageType("error");
    }
  }

  async function startRecording() {
    if (!selectedDevice || selectedDevice.device_type !== "camera") return;
    await api.startRecording(selectedDevice.id);
  }

  async function stopRecording() {
    if (!selectedDevice || selectedDevice.device_type !== "camera") return;
    await api.stopRecording(selectedDevice.id);
  }

  async function changeCameraSource() {
    if (!selectedDevice || selectedDevice.device_type !== "camera") return;

    const source = window.prompt("Enter 0 for webcam or paste an RTSP URL:", selectedDevice.rtsp_url ?? "");
    if (!source?.trim()) return;

    await api.updateDevice(selectedDevice.id, { rtsp_url: source.trim() });
    setStreamUrl(null);
    await onDeviceChanged();
  }

  async function startWebRTC() {
    if (!selectedDevice || selectedDevice.device_type !== "camera") return;

    const connection = new RTCPeerConnection();
    connection.addTransceiver("video", { direction: "recvonly" });
    connection.ontrack = (event) => {
      if (videoRef.current) {
        videoRef.current.srcObject = event.streams[0];
      }
    };

    const offer = await connection.createOffer();
    await connection.setLocalDescription(offer);
    const answer = await api.webrtcOffer(selectedDevice.id, offer);
    await connection.setRemoteDescription(answer);
    setPc(connection);
  }

  return (
    <section className="panel">
      <div className="section-header">
        <h2>Live Video</h2>
        <div className="actions">
          <button onClick={refreshStream}>Refresh</button>
          <button onClick={startRecording}>Start Recording</button>
          <button onClick={stopRecording}>Stop Recording</button>
          <button onClick={changeCameraSource}>Source</button>
          <button onClick={startWebRTC}>WebRTC</button>
        </div>
      </div>

      {message && <div className={`notice ${messageType}`}>{message}</div>}
      {streamUrl && <img className="video-frame" src={streamUrl} alt="MJPEG stream" />}

      <h3>WebRTC Fallback</h3>
      <video ref={videoRef} autoPlay playsInline controls muted />
    </section>
  );
}
