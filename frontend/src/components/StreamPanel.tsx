import { useEffect, useRef, useState } from "react";
import { api, liveUrl } from "../lib/api";
import { isVideoDevice } from "../lib/devices";
import type { Device } from "../types";
import { MjpegViewer } from "./MjpegViewer";
import { StreamControls } from "./StreamControls";
import { WebRTCViewer } from "./WebRTCViewer";

interface Props {
  selectedDevice: Device | null;
  onDeviceChanged: () => Promise<void>;
}

export function StreamPanel({ selectedDevice, onDeviceChanged }: Props) {
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [message, setMessage] = useState("Select a camera or drone to view the stream.");
  const [messageType, setMessageType] = useState<"info" | "error">("info");
  const [pc, setPc] = useState<RTCPeerConnection | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const videoSelected = isVideoDevice(selectedDevice);

  useEffect(() => {
    setStreamUrl(null);
    setMessage(videoSelected ? "Stream not loaded." : "Select a camera or drone to view the stream.");
    setMessageType("info");

    if (pc) {
      pc.close();
      setPc(null);
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, [videoSelected, selectedDevice?.id]);

  async function refreshStream() {
    setStreamUrl(null);

    if (!isVideoDevice(selectedDevice)) {
      setMessage("Select a camera or drone device to view a stream.");
      setMessageType("error");
      return;
    }

    if (!selectedDevice.rtsp_url?.trim()) {
      setMessage("This device does not have an RTSP URL.");
      setMessageType("error");
      return;
    }

    setMessage("Checking video stream...");
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
    if (!isVideoDevice(selectedDevice)) return;
    await api.startRecording(selectedDevice.id);
  }

  async function stopRecording() {
    if (!isVideoDevice(selectedDevice)) return;
    await api.stopRecording(selectedDevice.id);
  }

  async function changeCameraSource() {
    if (!isVideoDevice(selectedDevice)) return;

    const source = window.prompt("Enter 0 for webcam or paste an RTSP URL:", selectedDevice.rtsp_url ?? "");
    if (!source?.trim()) return;

    await api.updateDevice(selectedDevice.id, { rtsp_url: source.trim() });
    setStreamUrl(null);
    await onDeviceChanged();
  }

  async function startWebRTC() {
    if (!isVideoDevice(selectedDevice)) return;

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
        <StreamControls
          disabled={!videoSelected}
          onRefresh={refreshStream}
          onStartRecording={startRecording}
          onStopRecording={stopRecording}
          onChangeSource={changeCameraSource}
          onStartWebRTC={startWebRTC}
        />
      </div>

      <MjpegViewer message={message} messageType={messageType} streamUrl={streamUrl} />
      <WebRTCViewer videoRef={videoRef} />
    </section>
  );
}
