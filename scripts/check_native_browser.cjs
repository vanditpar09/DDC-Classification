/* Verify the saved native-pilot example; this is a UI check, not an accuracy test. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const base = 'http://127.0.0.1:8013';
const output = path.resolve(__dirname, '../data/research/multilingual-pilot-v1/experiment-v2');

(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1250, height: 1100}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') errors.push(message.text());
    });
    const response = await page.request.get(`${base}/api/sessions`);
    assert(response.ok(), 'Local server must be available');
    const books = await response.json();
    const hindi = books.find(book => book.title.startsWith('गबन'));
    assert(hindi, 'Saved Hindi UI example must exist');
    await page.goto(base);
    await page.waitForFunction(() => !busy && session);
    await page.getByRole('combobox', {name: 'Saved books', exact: true}).selectOption(hindi.id);
    await page.waitForFunction(() => !busy && session.combined_text.startsWith('गबन'));
    const labels = await page.evaluate(() => session.prediction.hierarchy.path.map(level => level.label));
    assert.deepEqual(labels, ['800', '890', '891']);
    assert.equal(await page.locator('.hierarchy-level').count(), 3);
    await page.locator('.score-note').filter({hasText: 'scores are uncalibrated'}).waitFor();
    assert.equal(await page.evaluate(() => session.prediction.model_version.experimental), true);
    await page.screenshot({path: path.join(output, 'local-website.png'), fullPage: true});
    assert.deepEqual(errors, [], 'Browser must have no script or console errors');
    fs.writeFileSync(path.join(output, 'browser-check.json'), JSON.stringify({
      checked_at: new Date().toISOString(),
      page_loaded: true,
      visible_three_levels: true,
      suggested_path: labels,
      experimental_note_visible: true,
      model: 'native_silver_v2',
      console_errors: errors,
      screenshot: 'local-website.png',
      physical_phone_test: false,
      accuracy_benchmark: false
    }, null, 2) + '\n');
    console.log('Website verified; screenshot and browser check saved.');
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
