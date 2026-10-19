const $ = id => document.getElementById(id);
let session = null, busy = false, sampleList = [];
let flushing = false, online = navigator.onLine;
let retryTimer = null, autoRetries = 0;
const pageNames = {cover:'Front cover', back_cover:'Back cover', contents:'Contents page'};
const actionNames = {capture_cover:'Waiting for evidence', request_page:'More subject information', recapture_region:'Recognition problem', reprocess_region:'Bounded OCR repair', switch_language:'Script mismatch', ready_for_review:'Suggestion available', human_review:'Human review'};

async function api(path, options={}) {
  const controller = new AbortController();
  const timer = setTimeout(()=>controller.abort(),120000);
  try {
    const response = await fetch(path, {...options, signal:controller.signal, cache:'no-store'});
    const result = await response.json().catch(()=>({detail:'The server could not complete this request. Inspect the saved trace before retrying.'}));
    if (!response.ok) {
      const error = new Error(typeof result.detail === 'string' ? result.detail : JSON.stringify(result.detail));
      error.status = response.status; error.detail = result.detail; throw error;
    }
    online=true; updateConnection(); return result;
  } finally { clearTimeout(timer); }
}
function el(tag, cls, text) { const node=document.createElement(tag); if(cls)node.className=cls; if(text!==undefined)node.textContent=text; return node; }
function showError(error) { $('error').textContent=error.message; if(error.status===401){ const link=el('a','','Sign in again');link.href='/__access';$('error').append(document.createTextNode(' '),link); } $('error').hidden=false; }
async function run(fn,label='Processing…') {
  if (busy) return;
  busy=true; $('error').hidden=true; $('busy').hidden=false; $('busy-label').textContent=label;
  document.querySelectorAll('button,select,textarea,input').forEach(b=>b.disabled=true);
  try { await fn(); } catch(error) { showError(error); }
  finally { busy=false; $('busy').hidden=true; document.querySelectorAll('button,select,textarea,input').forEach(b=>b.disabled=false); }
}
function mode(which) {
  if(which!=='photo')closeCamera();
  $('photo-input').hidden=which!=='photo'; $('text-input').hidden=which!=='text';
  $('photo-tab').classList.toggle('active',which==='photo'); $('text-tab').classList.toggle('active',which==='text');
}
$('photo-tab').onclick=()=>mode('photo'); $('text-tab').onclick=()=>mode('text');
async function keepSession(state) {
  session=state; render();
  await deviceStore('settings','put',state,'current-book');
  await refreshBooks();
}
async function refreshBooks() {
  try {
    const books=await api('/api/sessions');
    $('saved-books').replaceChildren();
    books.forEach(book=>{const option=el('option','',`${book.title} · ${book.page_count} pages`);option.value=book.id;$('saved-books').append(option);});
    if(session)$('saved-books').value=session.id;
  } catch(error) { online=false; updateConnection(); }
}
function clearReviewForm() { ['review-section','review-note','review-book-id'].forEach(id=>$(id).value=''); }
async function newBook() {
  closeCamera();
  await keepSession(await api('/api/sessions',{method:'POST'}));
  $('transcription').value=''; $('page-kind').value='cover'; clearReviewForm();
}
$('new-book').onclick=()=>run(newBook,'Starting a new book…');
$('saved-books').onchange=e=>run(async()=>{closeCamera();clearReviewForm();await keepSession(await api(`/api/sessions/${e.target.value}`));},'Opening saved book…');
$('reload-book').onclick=()=>run(async()=>{if(session)await keepSession(await api(`/api/sessions/${session.id}`));else await init();},'Reloading saved evidence…');
$('reclassify-book').onclick=()=>run(()=>enqueue('reclassify',{}),'Updating prediction from saved text…');
$('delete-book').onclick=()=>run(async()=>{
  if(!session || !confirm('Delete this book and its images, trace and pending evidence from this device? Export first if needed.'))return;
  const sid=session.id;
  await api(`/api/sessions/${sid}`,{method:'DELETE'});
  for(const op of await pendingList())if(op.sid===sid)await deviceStore('pending','delete',op.id);
  await deviceStore('settings','delete','current-book');session=null;
  await renderPending();await newBook();
},'Deleting this book…');
$('submit-text').onclick=()=>run(async()=>{
  if(!$('transcription').value.trim())throw new Error('Enter the visible text first.');
  await enqueue('text',{kind:$('page-kind').value,language:$('language').value,text:$('transcription').value});
  $('transcription').value='';
});
async function upload(file) {
  if(!file)return;
  if(file.size>12*1024*1024)throw new Error('Choose an image smaller than 12 MB.');
  await enqueue('image',{kind:$('page-kind').value,language:$('language').value,name:file.name||'capture.jpg'},file);
  $('file').value='';$('camera-file').value='';
}
$('open-camera').onclick=()=>{if(!busy)openCamera();};
$('close-camera').onclick=closeCamera;
$('retake-photo').onclick=openCamera;
$('take-photo').onclick=()=>takePhoto().catch(showError);
$('use-photo').onclick=()=>run(async()=>{const file=new File([previewBlob],'camera.jpg',{type:'image/jpeg'});await upload(file);closeCamera();},'Saving capture and reading its text…');
$('camera-file').onchange=e=>run(()=>upload(e.target.files[0]),'Saving the photograph…');
$('file').onchange=e=>run(()=>upload(e.target.files[0]),'Reading the image with local OCR…');
$('dropzone').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('file').click();}};
['dragover','dragenter'].forEach(evt=>$('dropzone').addEventListener(evt,e=>{e.preventDefault();$('dropzone').classList.add('dragging');}));
['dragleave','drop'].forEach(evt=>$('dropzone').addEventListener(evt,e=>{e.preventDefault();$('dropzone').classList.remove('dragging');}));
$('dropzone').addEventListener('drop',e=>run(()=>upload(e.dataTransfer.files[0]),'Reading the image with local OCR…'));

function updateConnection() { $('connection').textContent=online?'Connected to laptop':'Server unavailable · uploads saved on this device'; }
async function enqueue(type,data,blob) {
  if(!session)throw new Error('Connect once and open a book before capturing offline.');
  const pending=await pendingList();
  if(pending.length>=12 || pending.reduce((n,p)=>n+(p.blob?.size||0),blob?.size||0)>48*1024*1024)
    throw new Error('Pending storage limit reached (12 operations / 48 MB). Upload or delete pending evidence first.');
  const predecessor=pending.filter(p=>p.sid===session.id).slice(-1)[0];
  await deviceStore('pending','put',{id:operationID(),sid:session.id,revision:session.revision,type,data,blob,
                                    predecessor:predecessor?.id,created:Date.now(),status:'pending'});
  await renderPending();await flushPending();
}
async function renderPending() {
  const list=await pendingList();$('pending-panel').hidden=!list.length;$('pending-items').replaceChildren();
  for(const op of list){
    const item=el('li','pending-item');
    const title=`${op.type==='image'?'Photo':op.type==='reclassify'?'Update prediction':op.type} · ${pageNames[op.data.kind]||'Book'} · ${op.sid.slice(0,8)}`;
    const message=recoverableImageUpload(op)?'Your photo is saved on this device. Press Retry uploads to send it again.':op.error||'Saved on this device; waiting to upload.';
    item.append(el('strong','',title),el('span','muted',message));
    if(op.blob){const download=el('button','quiet','Save photo');download.onclick=()=>{const url=URL.createObjectURL(op.blob);const link=el('a');link.href=url;link.download=op.data.name||'capture.jpg';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};item.append(download);}
    const cancel=el('button','quiet','Remove pending item');
    cancel.onclick=()=>run(async()=>{
      if(!confirm('Remove this pending item? If the server already received it, this will not remove the saved evidence.'))return;
      // Dependants retain their revision and will conflict if the discarded request changed the server.
      await deviceStore('pending','delete',op.id);
      for(const next of await pendingList())if(next.predecessor===op.id){delete next.predecessor;await deviceStore('pending','put',next);}
      await renderPending();
    });item.append(cancel);$('pending-items').append(item);
  }
}
function missingImageBody(detail) {
  if(!Array.isArray(detail)||detail.length!==2)return false;
  const fields=detail.filter(v=>v.type==='missing'&&v.loc?.length===2&&v.loc[0]==='body').map(v=>v.loc[1]);
  return fields.includes('image')&&fields.includes('kind');
}
function recoverableImageUpload(op) {
  if(op.type!=='image'||!op.blob?.size)return false;
  if(op.failure==='empty-image-upload')return true;
  // Recover receipts written by the previous app version. Other validation and
  // revision conflicts stay blocked; operation IDs and revisions never change.
  const suffix=' Reload the book to inspect saved evidence.';
  const end=op.error?.indexOf(suffix);
  if(!(end>0))return false;
  try{return missingImageBody(JSON.parse(op.error.slice(0,end)));}catch{return false;}
}
async function imageUploadBody(op) {
  if(!op.blob?.size)throw new Error('The saved photo is unavailable. Keep the original and capture it again.');
  // WebKit #319985 can silently send an empty multipart body for a File read
  // from IndexedDB. Copy its bytes into a memory-backed Blob before sending.
  const bytes=await op.blob.arrayBuffer();
  if(bytes.byteLength!==op.blob.size)throw new Error('The saved photo could not be read completely. It remains on this device.');
  const image=new Blob([bytes],{type:op.blob.type||'image/jpeg'});
  const body=new FormData();
  body.append('image',image,op.data.name||'capture.jpg');body.append('kind',op.data.kind);body.append('language',op.data.language);
  return body;
}
async function flushPending() {
  if(flushing || !navigator.onLine)return;
  flushing=true;
  let advanced=false, interrupted=false, networkFailure=false;
  try {
    for(const op of await pendingList()){
      // Stop a book's chain after a conflict; never silently overwrite newer evidence.
      if(op.status==='blocked' || op.predecessor)continue;
      const headers={'Idempotency-Key':op.id,'X-Book-Revision':String(op.revision)};
      let path=`/api/sessions/${op.sid}/${op.type}`,body;
      if(op.type==='image'){
        body=await imageUploadBody(op);
      }else{
        headers['Content-Type']='application/json';body=JSON.stringify(op.data);
        if(op.type==='repair')path=`/api/sessions/${op.sid}/pages/${op.data.pid}/repair`;
      }
      try{
        const state=await api(path,{method:'POST',headers,body});
        // Release the next item before deleting the receipt-bearing head. Replays are safe.
        for(const next of await pendingList())if(next.predecessor===op.id){next.revision=state.revision;delete next.predecessor;await deviceStore('pending','put',next);}
        await deviceStore('pending','delete',op.id);
        autoRetries=0;
        advanced=true;
        if(session?.id===op.sid)await keepSession(state);
      }catch(error){
        if(error.status===401){op.error=error.message;showError(error);}
        else if([503,504].includes(error.status)){networkFailure=true;online=false;updateConnection();op.error=error.message;}
        else if(error.status===422&&op.type==='image'&&missingImageBody(error.detail)){
          op.status='blocked';op.failure='empty-image-upload';
          op.error='Your photo is saved on this device, but the browser sent an empty upload. Reload this page, then press Retry uploads. You do not need to remove the photo.';
        }
        else if(error.status){op.status='blocked';op.error=error.message+' Reload the book to inspect saved evidence. Remove this item before submitting a corrected capture.';}
        else {networkFailure=true;online=false;updateConnection();op.error='Connection interrupted. The same upload will be retried safely while this app is open, or when you press Retry uploads.';}
        await deviceStore('pending','put',op);interrupted=true;break;
      }
    }
  }finally{flushing=false;await renderPending();}
  if(networkFailure&&!document.hidden&&autoRetries<3){
    clearTimeout(retryTimer);
    const delay=[2000,5000,15000][autoRetries++];
    retryTimer=setTimeout(()=>{if(!busy)run(flushPending,'Retrying pending evidence…');},delay);
  }
  // Success may have released a dependent capture from the initial snapshot.
  if(advanced&&!interrupted&&(await pendingList()).some(op=>op.status==='pending'&&!op.predecessor))await flushPending();
}
$('retry-pending').onclick=()=>{
  autoRetries=0;clearTimeout(retryTimer);
  run(async()=>{
    for(const op of await pendingList())if(op.status==='blocked'&&recoverableImageUpload(op)){
      op.status='pending';delete op.error;delete op.failure;await deviceStore('pending','put',op);
    }
    await flushPending();
  },'Sending pending evidence…');
};
window.addEventListener('online',()=>{online=true;autoRetries=0;clearTimeout(retryTimer);updateConnection();if(!busy)run(flushPending,'Resuming pending evidence…');});
window.addEventListener('offline',()=>{online=false;updateConnection();});
document.addEventListener('visibilitychange',()=>{clearTimeout(retryTimer);if(!document.hidden&&!busy){autoRetries=0;run(flushPending,'Resuming pending evidence…');}});
$('save-review').onclick=()=>run(async()=>{
  if(!/^[0-9]{3}$/.test($('review-section').value)||!$('reviewer').value.trim())throw new Error('Enter a three-digit section and reviewer name.');
  await enqueue('review',{section:$('review-section').value,reviewer:$('reviewer').value,
                         note:$('review-note').value,book_id:$('review-book-id').value});
},'Saving the review…');

function renderHierarchy(container, hierarchy, catalog=false) {
  hierarchy.path.forEach(v=>{
    const card=el('div','hierarchy-level'),head=el('div','hierarchy-heading');
    const available=v.supported&&v.label;
    const status=catalog?'Review required':available?(v.review_ready?'For review':'Provisional'):'No trained code';
    head.append(el('strong','',`L${v.level} · ${['','Class','Division','Section'][v.level]}`),el('span','tag'+(v.review_ready?'':' bad'),status));
    card.append(head,el('div','hierarchy-code',available?v.label:'Unavailable'));
    if(Number.isFinite(v.score)){
      const score=v.level===1?`${(v.score*100).toFixed(1)}% model score`:`${(v.score*100).toFixed(1)}% conditional on ${v.parent}`;
      card.append(el('p','muted',score+(Number.isFinite(v.training_groups)?` · ${v.training_groups} training book groups`:'')));
    }
    if(!available)card.append(el('p','muted',v.reason||'This branch has no trained code.'));
    if(v.level>1&&v.top3?.length)card.append(el('p','muted','Candidates: '+v.top3.map(c=>`${c.label||'Other / rare'} (${(c.score*100).toFixed(0)}%)`).join(' · ')));
    container.append(card);
  });
}

function render() {
  const {decision:d,work:w,prediction:p}=session;
  $('passes').replaceChildren(document.createTextNode(w.ocr_passes),el('span','', '/ 6'));
  $('pixels').textContent=(w.pixels/1e6).toFixed(1);$('calls').textContent=w.classifier_calls;
  $('time').replaceChildren(document.createTextNode(w.seconds.toFixed(1)),el('span','','s'));
  $('decision-title').textContent=d.title;$('decision-reason').textContent=d.reason;
  const button=$('action-button'); button.hidden=!['request_page','recapture_region','reprocess_region','switch_language'].includes(d.action);
  if(d.action==='reprocess_region'||d.action==='switch_language') {
    button.textContent=d.action==='switch_language'?'Retry with selected language':'Retry OCR on the affected region';
    button.onclick=()=>run(()=>enqueue('repair',{pid:d.page_id,language:$('language').value}),'Reprocessing the image locally…');
  }else {button.textContent=d.action==='recapture_region'?'Choose a clearer photograph':'Add '+(pageNames[d.requested_page]||'page').toLowerCase()+'';button.onclick=()=>{$('page-kind').value=d.requested_page;mode('photo');$('dropzone').scrollIntoView({behavior:'smooth',block:'center'});$('file').click();};}
  const predictions=$('predictions');predictions.replaceChildren();
  if(p?.hierarchy){
    const catalog=p.result_source==='local_catalog';
    // Display available trained candidates even below the review threshold.
    // The saved threshold-qualified path and controller decision stay separate.
    const h=catalog?p.hierarchy:(p.model_suggestion?.hierarchy||p.hierarchy);
    if(!catalog&&h.review_level<h.target_level)predictions.append(el('p','score-note','Provisional prediction — below the review threshold. These codes may be wrong; add subject evidence and review them.'));
    if(p.catalog_match?.status==='matched'){
      const record=p.catalog_match.record;
      predictions.append(el('p','score-note',`Catalog match: ${record.title} · ${record.authors.join(', ')}. Source code: ${record.ddc_raw.join(', ')}. Confirm the edition.`));
      for(const url of record.source_urls||[]){
        if(!/^https:\/\/openlibrary\.org\//.test(url))continue;
        const link=el('a','','View catalog record');link.href=url;link.target='_blank';link.rel='noopener noreferrer';predictions.append(link);
      }
    }
    renderHierarchy(predictions,h,catalog);
    const last=h.path.at(-1);
    if(!catalog&&last?.level===3&&Number.isFinite(last.path_score))predictions.append(el('p','score-note',`Combined path score: ${(last.path_score*100).toFixed(1)}% (product of model scores; uncalibrated).`));
    predictions.append(el('p','score-note',p.result_source==='local_catalog'?'The catalog code is not a model probability. All assignments require confirmation.':p.model_version?.experimental?'Experimental model: scores are uncalibrated. Check the suggested codes against the book and catalog evidence.':h.review_level?`Review threshold passed through level ${h.review_level}. All assignments still require human confirmation.`:'No level passes the review threshold yet.'));

    if(p.result_source!=='local_catalog')predictions.append(el('h3','broad-heading','Broad class alternatives'));
  }
  if(p){
    let alternatives=predictions;
    if(p.result_source==='local_catalog'){
      alternatives=el('details','limitations');
      alternatives.append(el('summary','','Raw model alternatives'));
      if(p.model_suggestion?.hierarchy){
        alternatives.append(el('p','score-note','Provisional learned-model path, separate from the catalog code. Scores are uncalibrated.'));
        renderHierarchy(alternatives,p.model_suggestion.hierarchy);
      }
      predictions.append(alternatives);
    }
    p.top3.forEach((v,i)=>{const row=el('div','prediction'),label=el('div','prediction-label');label.append(el('strong','',v.label),el('span','',v.name),el('span','',`${(v.score*100).toFixed(1)}%`));const bar=el('div','bar'),fill=el('i');fill.style.width=(v.score*100)+'%';bar.append(fill);row.append(label,bar);alternatives.append(row);});if(p.truncated)predictions.append(el('p','muted','Long text: the encoder read only the first 512 tokens.'));}
  else predictions.append(el('p','muted','Suggestions appear when readable evidence is available.'));
  $('combined-text').textContent=session.combined_text||'No usable text yet.';$('text-count').textContent=session.combined_text.length+' characters';
  const pages=$('pages');pages.replaceChildren();
  [...session.pages].sort((a,b)=>b.sequence-a.sequence).forEach(page=>{
    const card=el('article','panel'),head=el('div','page-head');
    head.append(el('span','',pageNames[page.kind]),el('span','tag'+(!page.usable||page.duplicate?' bad':''),page.duplicate?'Duplicate evidence':page.source==='transcription'?'Human transcription':page.usable?'Text extracted · check photo':'OCR needs attention'));
    const layout=el('div','page-layout'),preview=el('div','preview'),body=el('div');
    if(page.source==='ocr'){
      const img=el('img');img.src=`/api/sessions/${session.id}/pages/${page.id}/image`;img.alt=pageNames[page.kind];preview.append(img);
      const r=page.quality?.region;
      if(r&&!page.usable){const region=el('div','region');region.style.left=(r.left/r.image_width*100)+'%';region.style.top=(r.top/r.image_height*100)+'%';region.style.width=(r.width/r.image_width*100)+'%';region.style.height=(r.height/r.image_height*100)+'%';preview.append(region);}
    }else preview.append(el('div','no-image','Aa'));
    body.append(el('div','ocr-text',page.text||'No text recognized.'));
    if(page.quality){
      const q=page.quality;
      const uncertain=q.low_confidence_fraction===undefined?'':` · ${(q.low_confidence_fraction*100).toFixed(0)}% low-confidence words`;
      body.append(el('div','quality',`Recognition score ${q.ocr_confidence.toFixed(1)} / 100 (not accuracy) · ${q.word_count} words · ${page.language}${uncertain}\nCharacter height ${q.median_character_height.toFixed(0)} px · ${page.repairs} repair(s)`));
      if(q.capture?.page_detected)body.append(el('p','muted','Book area detected. Check that the title and author are included.'));
    }
    if(page.source==='ocr'&&page.repairs<1&&session.work.ocr_passes<6){
      const retry=el('button','quiet','Read photo again');
      retry.onclick=()=>run(()=>enqueue('repair',{pid:page.id,language:page.language}),'Reading the saved photograph again…');
      body.append(retry);
    }
    layout.append(preview,body);card.append(head,layout);pages.append(card);
  });
  const reviewed=session.reviews?.slice(-1)[0];
  $('review-status').textContent=reviewed?`Last review: ${reviewed.class} ${reviewed.division} ${reviewed.section} by ${reviewed.reviewer}. Recorded against evidence revision ${reviewed.evidence_revision}; current revision ${session.revision}.`:'No reviewed label recorded yet.';
  const events=$('events');events.replaceChildren();
  if(!session.events.length)events.append(el('li','empty','No decisions yet.'));
  session.events.slice().reverse().forEach(e=>{const item=el('li');item.append(el('b','',e.event==='duplicate_upload_ignored'?'Duplicate image skipped':(actionNames[e.action]||e.action||e.event.replaceAll('_',' '))),el('span','',e.reason));events.append(item);});
  $('export').href=`/api/sessions/${session.id}/export`;
  if(p?.model_version)$('text-count').textContent+=` · ${p.token_count} tokens · ${p.model_version.name}`;
}
async function init() {
  if(location.protocol==='file:')throw new Error('Start the local server and open http://127.0.0.1:8011. This page cannot run from a file URL.');
  if('serviceWorker' in navigator && window.isSecureContext)navigator.serviceWorker.register('/sw.js').catch(error=>{$('install-hint').textContent='Offline installation unavailable: '+error.message;});
  const saved=await deviceStore('settings','get','current-book');
  if(saved){session=saved;render();}
  let status;
  try{status=await api('/api/status');await deviceStore('settings','put',status,'server-status');}
  catch(error){if(error.status===401)throw error;online=false;updateConnection();status=await deviceStore('settings','get','server-status');}
  if(!status){await renderPending();throw new Error('Connect to the local server once to prepare this device.');}
  $('language').replaceChildren();
  Object.entries(status.languages).forEach(([k,v])=>{const o=el('option','',v);o.value=k;$('language').append(o);});
  if(!status.model_files_present)throw new Error('The improved model is missing. See prototype/README.md for setup.');
  if(online){
    if(saved){try{await keepSession(await api(`/api/sessions/${saved.id}`));}catch(error){if(error.status===404){await newBook();}else throw error;}}
    else await newBook();
    sampleList=await api('/api/samples');
  }
  $('sample-buttons').replaceChildren();
  sampleList.forEach(sample=>{const b=el('button','',sample.name);b.onclick=()=>run(async()=>{$('page-kind').value=sample.kind;$('language').value=sample.language;const blob=await(await fetch('/samples/'+sample.file)).blob();await upload(new File([blob],sample.file,{type:'image/png'}));},'Reading example image…');$('sample-buttons').append(b);});
  await renderPending();await flushPending();
}
run(init,'Connecting…');
