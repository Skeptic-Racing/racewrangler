type LegacyGetUserMedia = (
  constraints: MediaStreamConstraints,
  onSuccess: (stream: MediaStream) => void,
  onError: (error: unknown) => void,
) => void;

interface LegacyNavigator extends Navigator {
  getUserMedia?: LegacyGetUserMedia;
  webkitGetUserMedia?: LegacyGetUserMedia;
  mozGetUserMedia?: LegacyGetUserMedia;
  msGetUserMedia?: LegacyGetUserMedia;
}

function getLegacyGetUserMedia(): LegacyGetUserMedia | null {
  const nav = navigator as LegacyNavigator;
  return nav.getUserMedia || nav.webkitGetUserMedia || nav.mozGetUserMedia || nav.msGetUserMedia || null;
}

function getUserMediaCompat(constraints: MediaStreamConstraints): Promise<MediaStream> {
  if (navigator.mediaDevices?.getUserMedia) {
    return navigator.mediaDevices.getUserMedia(constraints);
  }

  const legacyGetUserMedia = getLegacyGetUserMedia();
  if (!legacyGetUserMedia) {
    throw new Error('Camera API is not supported in this browser context');
  }

  return new Promise((resolve, reject) => {
    legacyGetUserMedia.call(navigator as LegacyNavigator, constraints, resolve, reject);
  });
}

export async function openPreferredCamera(): Promise<MediaStream> {
  try {
    return await getUserMediaCompat({
      video: { facingMode: { ideal: 'environment' } },
      audio: false,
    });
  } catch {
    return getUserMediaCompat({ video: true, audio: false });
  }
}

export function stopMediaStream(stream: MediaStream | null | undefined) {
  stream?.getTracks().forEach(track => track.stop());
}

export async function attachStreamToVideo(video: HTMLVideoElement, stream: MediaStream): Promise<void> {
  video.muted = true;
  video.autoplay = true;
  video.playsInline = true;
  video.setAttribute('playsinline', 'true');
  video.setAttribute('webkit-playsinline', 'true');
  video.srcObject = stream;

  await new Promise<void>((resolve, reject) => {
    let settled = false;
    const timeout = window.setTimeout(() => {
      cleanup();
      reject(new Error('Timed out waiting for camera preview'));
    }, 4000);

    const done = () => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve();
    };

    const fail = () => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(new Error('Camera stream failed to initialize preview'));
    };

    const cleanup = () => {
      window.clearTimeout(timeout);
      video.removeEventListener('loadedmetadata', onReady);
      video.removeEventListener('canplay', onReady);
      video.removeEventListener('error', fail);
    };

    const onReady = () => {
      if (video.videoWidth > 0 && video.videoHeight > 0) {
        done();
      }
    };

    video.addEventListener('loadedmetadata', onReady);
    video.addEventListener('canplay', onReady);
    video.addEventListener('error', fail);
    onReady();
  });

  await video.play();
}
