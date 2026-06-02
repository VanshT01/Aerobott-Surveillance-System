interface Props {
  disabled: boolean;
  onRefresh: () => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onChangeSource: () => void;
  onStartWebRTC: () => void;
}

export function StreamControls({
  disabled,
  onRefresh,
  onStartRecording,
  onStopRecording,
  onChangeSource,
  onStartWebRTC
}: Props) {
  return (
    <div className="actions">
      <button disabled={disabled} onClick={onRefresh}>Refresh</button>
      <button disabled={disabled} onClick={onStartRecording}>Start Recording</button>
      <button disabled={disabled} onClick={onStopRecording}>Stop Recording</button>
      <button disabled={disabled} onClick={onChangeSource}>Source</button>
      <button disabled={disabled} onClick={onStartWebRTC}>WebRTC</button>
    </div>
  );
}
