/* Explicit device storage, separate from the service worker's public asset cache. */
const localDB = new Promise((resolve, reject) => {
  const request = indexedDB.open('fieldnote-local-v1', 1);
  request.onupgradeneeded = () => {
    request.result.createObjectStore('pending', {keyPath:'id'});
    request.result.createObjectStore('settings');
  };
  request.onsuccess = () => resolve(request.result);
  request.onerror = () => reject(new Error('Device storage is unavailable. Enable site storage to retain captures.'));
});
async function deviceStore(store, method, value, key) {
  const db = await localDB;
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, method.startsWith('get') ? 'readonly' : 'readwrite');
    const bucket = tx.objectStore(store);
    const request = key === undefined ? bucket[method](value) : bucket[method](value, key);
    tx.oncomplete = () => resolve(request.result);
    tx.onerror = () => reject(new Error('Could not save on this device. Storage may be full; keep your original capture.'));
    tx.onabort = tx.onerror;
  });
}
const pendingList = async () => (await deviceStore('pending','getAll')).sort((a,b)=>a.created-b.created);
function operationID() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, b=>b.toString(16).padStart(2,'0')).join('');
}
