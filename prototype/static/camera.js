let cameraStream = null, cameraGeneration = 0, previewBlob = null, previewURL = null;
function stopCamera() {
  cameraGeneration++;
  if (cameraStream) cameraStream.getTracks().forEach(track=>track.stop());
  cameraStream = null;
  document.getElementById('camera-video').srcObject = null;
}
function closeCamera() {
  stopCamera();
  if(previewURL) URL.revokeObjectURL(previewURL);
  previewURL = null; previewBlob = null;
  document.getElementById('camera-panel').hidden = true;
}
async function openCamera() {
  const video = document.getElementById('camera-video');
  closeCamera();
  document.getElementById('camera-panel').hidden = false;
  document.getElementById('camera-still').hidden = true;
  video.hidden = false;
  document.getElementById('take-photo').hidden = false;
  document.getElementById('take-photo').disabled = true;
  document.getElementById('use-photo').hidden = true;
  document.getElementById('retake-photo').hidden = true;
  document.getElementById('camera-message').textContent = 'Allow camera access. Keep the page flat and fill the frame with readable text.';
  const generation = cameraGeneration;
  try {
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia)
      throw new Error('Live camera requires HTTPS on phones. Use “Take a photo / choose file” below, or see the local phone setup instructions.');
    const stream = await navigator.mediaDevices.getUserMedia({audio:false, video:{facingMode:{ideal:'environment'},width:{ideal:2560},height:{ideal:1920}}});
    if(generation!==cameraGeneration) { stream.getTracks().forEach(track=>track.stop()); return; }
    cameraStream = stream; video.srcObject = stream;
    await video.play();
    if(generation!==cameraGeneration) return;
    document.getElementById('take-photo').disabled = false;
  } catch(error) {
    if(generation!==cameraGeneration) return;
    stopCamera();
    document.getElementById('camera-message').textContent = error.name==='NotAllowedError'
      ? 'Camera permission was denied. Allow camera access in the browser, or use the photo picker below.' : error.message;
  }
}
async function takePhoto() {
  const video = document.getElementById('camera-video');
  if(!video.videoWidth || !video.videoHeight) throw new Error('Camera is not ready. Try again.');
  const generation = cameraGeneration;
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth; canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video,0,0);
  const blob = await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',0.95));
  if(generation!==cameraGeneration) return;
  if(!blob) throw new Error('Could not capture this frame. Use the photo picker.');
  previewBlob = blob; previewURL = URL.createObjectURL(blob);
  const still = document.getElementById('camera-still');
  still.src = previewURL; still.hidden = false; video.hidden = true;
  document.getElementById('camera-message').textContent = `${canvas.width} × ${canvas.height} · Check focus and small print before using this photo. No resizing applied.`;
  document.getElementById('take-photo').hidden = true;
  document.getElementById('retake-photo').hidden = false;
  document.getElementById('use-photo').hidden = false;
  stopCamera();
}
document.addEventListener('visibilitychange',()=>{if(document.hidden)closeCamera();});
window.addEventListener('pagehide',closeCamera);
