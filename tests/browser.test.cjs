/* Optional real-browser acceptance check. Requires an installed Playwright and Chromium.
   Not run in environments where browser launch is denied. Never bypass a denial. */
const {chromium} = require('playwright');
const {pathToFileURL} = require('node:url');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(path.resolve(__dirname,'../index.html')).href);
    assert.equal(await page.locator('.sizes').evaluate(e=>getComputedStyle(e).display),'grid');
    assert.equal(await page.locator('.sizes').evaluate(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length),3);
    assert.equal(await page.locator('#active-filters').evaluate(e=>e.parentElement.className),'toolbar');
    assert.equal(await page.locator('#sort').inputValue(),'recommended');
    assert.equal(await page.locator('.specimen-header h2').first().innerText(),'SimSun 中易宋体原生点阵 12×12');
    const total = await page.locator('.specimen').count();
    assert(total > 0);
    assert.equal(await page.locator('.specimen-image').count(), total*2);
    const wordmark = await page.locator('.wordmark img').evaluate(e=>({width:e.width,height:e.height}));
    assert.deepEqual(wordmark,{width:192,height:48});
    await page.locator('.specimen-image').first().evaluate(image => image.decode());
    assert.equal(await page.locator('.specimen-header h2').first().evaluate(e=>getComputedStyle(e).fontWeight),'400');
    const original = await page.locator('.sample-native img').first().evaluate(e=>({width:e.width,natural:e.naturalWidth}));
    assert.equal(original.width,original.natural);
    const zoom = page.locator('.zoom-control').first(); await zoom.selectOption('4');
    assert.equal(await page.locator('.sample-enlarged img').first().evaluate(e=>e.width),original.natural*4);
    await page.locator('#filter-groups input[type=radio]').nth(1).check();
    assert(await page.locator('.specimen').count() < total);
    assert.equal(await page.locator('#active-filters button').count(),1);
    const bounds = await page.locator('#active-filters').boundingBox();
    const familyBounds = await page.locator('#family').boundingBox();
    assert(Math.abs(bounds.y-familyBounds.y)<20); // A single chip shares the desktop toolbar row.
    assert(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth));
    assert.equal(await page.locator('#filter-groups input[type=radio]:checked').count(),1);
    await page.locator('#filter-groups input[type=radio]').nth(2).check();
    assert.equal(await page.locator('#filter-groups input[type=radio]:checked').count(),1);
    await page.locator('#active-filters button').first().click();
    assert.equal(await page.locator('.specimen').count(),total);
    assert.equal(await page.locator('#filter-groups input[type=radio]:checked').inputValue(),'');
    await page.locator('.detail-button').first().click();
    assert(await page.locator('#detail-dialog').evaluate(e=>e.open));
    assert(await page.locator('#detail-content').innerText());
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#detail-dialog').evaluate(e=>e.open),false);
    await page.locator('#about-open').click();
    assert(await page.locator('#about-dialog').evaluate(e=>e.open));
    await page.keyboard.press('Escape');
    await page.screenshot({path:path.resolve(__dirname,'../../bitmap-desktop-review.png'),fullPage:false});
    await page.setViewportSize({width:390,height:844});
    await page.locator('#filters-open').click();
    assert.equal(await page.locator('#filters-open').getAttribute('aria-expanded'),'true');
    await page.locator('#filter-groups input[type=radio]').nth(1).check();
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#filters-open').getAttribute('aria-expanded'),'false');
    assert.equal(await page.locator('#main').evaluate(e=>e.inert),false);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path:path.resolve(__dirname,'../../bitmap-mobile-review.png'),fullPage:false});
    assert.deepEqual(errors,[]);
    console.log(`Browser acceptance passed: ${total} rows, original/integer dimensions, filters, dialogs, mobile drawer and no page errors.`);
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
