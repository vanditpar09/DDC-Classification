/* Local phone-size UI test using the saved real cover. Test book is disposable. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const base = process.env.FIELDNOTE_TEST_URL || 'http://127.0.0.1:8013';
const output = process.env.FIELDNOTE_BROWSER_OUTPUT || path.resolve(__dirname,'../output/ocr-upgrade-v1');
fs.mkdirSync(output,{recursive:true});

(async()=>{
  const browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:390,height:844},extraHTTPHeaders:{Origin:base}});
  const page=await context.newPage();
  const errors=[];let sid;
  page.on('pageerror',error=>errors.push(error.message));
  try {
    await page.goto(base);await page.waitForFunction(()=>!busy&&session);
    sid=await page.evaluate(()=>session.id);
    const fixture=path.resolve(__dirname,'../data/research/ocr-upgrade-v1/fixtures/phone-english-cover.png');
    await page.locator('#file').setInputFiles(fs.existsSync(fixture)?fixture:path.resolve(__dirname,'../output/ocr-phone-review/english-original.png'));
    await page.waitForFunction(()=>!busy&&!flushing&&session.pages.length===1,null,{timeout:120000});
    let state=await page.evaluate(()=>JSON.parse(JSON.stringify(session)));
    const text=state.combined_text.replace(/\s+/g,' ').toLowerCase();
    assert(text.includes('the kite runner')&&text.includes('khaled hosseini'));
    assert(!['control','option','command'].some(word=>text.includes(word)));
    assert.equal(await page.locator('.hierarchy-level').count(),3);
    assert.deepEqual(state.prediction.hierarchy.path.map(row=>row.label),['800','810','813']);
    assert.equal(state.prediction.result_source,'local_catalog');
    await page.getByRole('link',{name:'View catalog record',exact:true}).waitFor();
    await page.getByText('Book area detected. Check that the title and author are included.',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Read photo again',exact:true}).click();
    await page.waitForFunction(()=>!busy&&!flushing&&session.pages[0].repairs===1,null,{timeout:120000});
    const repaired=await page.evaluate(()=>JSON.parse(JSON.stringify(session)));
    assert.equal(repaired.work.ocr_passes,state.work.ocr_passes+1);
    assert.equal(repaired.work.classifier_calls,state.work.classifier_calls);
    assert.equal(repaired.page_history.length,1);
    assert.equal(await page.getByRole('button',{name:'Read photo again',exact:true}).count(),0);
    assert.equal(await page.evaluate(async()=>(await pendingList()).length),0);
    await page.screenshot({path:path.join(output,'phone-result.png'),fullPage:true});
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(output,'browser-check.json'),JSON.stringify({passed:true,
      checked_at:new Date().toISOString(),title_recovered:true,author_recovered:true,background_text_removed:true,
      three_ddc_levels_visible:true,saved_photo_reread_works:true,one_repair_limit_enforced:true,
      physical_phone_test:false,real_phone_source_image:true,reader:state.pages[0].quality.engine,
      suggested_path:state.prediction.hierarchy.path.map(level=>level.label),
      catalog_regression_validated:true,result_source:state.prediction.result_source,
      classification_accuracy_validated:false,page_errors:errors},null,2)+'\n');
    console.log('PASS: real-cover OCR, three levels, saved-photo reread, and one-repair limit.');
  } finally {
    if(sid)assert.equal((await context.request.delete(`${base}/api/sessions/${sid}`)).status(),200);
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
