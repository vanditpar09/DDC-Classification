/* Saved-photo recovery through IndexedDB and real local OCR, not a phone benchmark. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = 'http://127.0.0.1:8013';
const output = path.resolve(__dirname, '../output/phone-upload-tests');
const missing = [{type:'missing',loc:['body','image'],msg:'Field required',input:null},
                 {type:'missing',loc:['body','kind'],msg:'Field required',input:null}];

(async () => {
  fs.mkdirSync(output, {recursive:true});
  const browser = await chromium.launch({headless:true});
  const context = await browser.newContext({viewport:{width:390,height:844},extraHTTPHeaders:{Origin:base}});
  const page = await context.newPage();
  const errors = [], requests = [];
  let sid;
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(base);
    await page.waitForFunction(() => !busy && session);
    sid = await page.evaluate(() => session.id);
    let fail = true;
    await page.route('**/api/sessions/*/image', async route => {
      requests.push({key:route.request().headers()['idempotency-key'],revision:route.request().headers()['x-book-revision']});
      if(fail){fail=false;return route.fulfill({status:422,contentType:'application/json',body:JSON.stringify({detail:missing})});}
      return route.continue();
    });
    await page.locator('#page-kind').selectOption('back_cover');
    await page.locator('#file').setInputFiles(path.resolve(__dirname,'../prototype/samples/informative_back.png'));
    await page.waitForFunction(() => !busy && !flushing);
    await page.getByText('Your photo is saved on this device. Press Retry uploads to send it again.', {exact:true}).waitFor();
    const pending = await page.evaluate(async () => {
      const op=(await pendingList())[0];
      const body=await imageUploadBody(op);
      const original=new Uint8Array(await op.blob.arrayBuffer());
      const sent=new Uint8Array(await body.get('image').arrayBuffer());
      return {id:op.id,status:op.status,failure:op.failure,size:op.blob.size,
        identical_bytes:original.length===sent.length&&original.every((value,i)=>value===sent[i]),
        kind:body.get('kind'),language:body.get('language')};
    });
    assert(pending.size>0 && pending.identical_bytes);
    assert.equal(pending.status,'blocked');assert.equal(pending.failure,'empty-image-upload');
    assert.equal(pending.kind,'back_cover');assert.equal(pending.language,'eng');
    // Restore the exact legacy receipt that the user's phone currently holds.
    await page.evaluate(async detail => {
      const op=(await pendingList())[0];delete op.failure;
      op.error=JSON.stringify(detail)+' Reload the book to inspect saved evidence. Remove this item before submitting a corrected capture.';
      await deviceStore('pending','put',op);
    }, missing);
    await page.reload();await page.waitForFunction(() => !busy && !flushing);
    assert(!(await page.locator('#pending-items').innerText()).includes('Field required'));
    await page.getByText('Your photo is saved on this device. Press Retry uploads to send it again.', {exact:true}).waitFor();
    assert.equal(await page.evaluate(async () => (await pendingList())[0].id),pending.id);
    await page.getByRole('button',{name:'Retry uploads',exact:true}).click();
    await page.waitForFunction(() => !busy && !flushing && session.pages.length===1, null, {timeout:120000});
    assert.equal(await page.evaluate(async () => (await pendingList()).length),0);
    assert.equal(await page.evaluate(() => session.work.classifier_calls),1);
    assert.deepEqual(requests[0],requests[1]);
    // A genuine stale revision must remain blocked; Retry must not overwrite it.
    await page.evaluate(async () => {
      const op={id:operationID(),sid:session.id,revision:0,type:'image',data:{kind:'cover',language:'eng',name:'test.png'},
        blob:new Blob(['test'],{type:'image/png'}),created:Date.now(),status:'blocked',error:'Book revision changed. Reload the book to inspect saved evidence.'};
      await deviceStore('pending','put',op);await renderPending();
    });
    await page.getByRole('button',{name:'Retry uploads',exact:true}).click();
    await page.waitForFunction(() => !busy && !flushing);
    assert.equal(requests.length,2);
    assert.equal(await page.evaluate(async () => (await pendingList())[0].status),'blocked');
    await page.evaluate(async () => {for(const op of await pendingList())await deviceStore('pending','delete',op.id);await renderPending();});
    await page.screenshot({path:path.join(output,'recovered.png'),fullPage:true});
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(output,'results.json'),JSON.stringify({
      passed:true,checked_at:new Date().toISOString(),checks:[
        'Missing image/body fields produce a readable message and preserve the photo',
        'Memory-backed multipart upload preserves every image byte and both text fields',
        'Exact legacy blocked receipt survives reload and recovers with Retry uploads',
        'Retry retains the original operation ID and revision; one page and classifier call saved',
        'Unrelated revision conflicts remain blocked'
      ],physical_phone_test:false,page_errors:errors
    },null,2)+'\n');
    console.log('PASS: saved-photo recovery, exact legacy error, byte integrity, and conflict protection.');
  } finally {
    if(sid)assert.equal((await context.request.delete(`${base}/api/sessions/${sid}`)).status(),200);
    await browser.close();
  }
})().catch(error => {console.error(error);process.exitCode=1;});
