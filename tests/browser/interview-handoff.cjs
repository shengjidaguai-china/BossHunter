const http = require('node:http');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '../..');
const buildDir = process.env.BROWSER_BUILD_DIR || path.join(root, 'src/bosshunter/web/frontend/dist');
const artifactDir = path.join(root, 'output/playwright');
const job = {
  id: 'interview-fixture-job', source_platform: 'boss', title: '合成测试岗位',
  company: '合成测试公司', salary: '10-15K·13薪', city: '测试城', education: '本科',
  experience: '不限', jd: '纯本地合成 JD。负责测试设计与质量保障。\n不涉及真实招聘信息。',
  score: 80, score_reason: 'PRIVATE_SCORE_REASON', greeting: 'PRIVATE_GREETING',
  status: 'approved', hr_name: 'PRIVATE_HR_NAME', hr_title: 'PRIVATE_HR_TITLE',
  hr_active: '', company_size: '', company_industry: '', url: '',
  created_at: '2026-09-06 00:00:00', resume_path: 'PRIVATE_RESUME_PATH',
  resume: 'PRIVATE_RESUME', api_key: 'PRIVATE_API_KEY', chats: ['PRIVATE_CHAT'],
};
const expectedJob = {
  company: job.company, target_role: job.title, city: job.city,
  salary: job.salary, education: job.education, jd: job.jd,
};
const workbench = {
  funnel: {}, funnel_today: {}, pending_confirmation: [], pending_greetings: [],
  send_errors: [], needs_resume: [], send_quota: { daily_limit: 30, sent: 0, remaining: 30, exhausted: false },
  task: null, last_task: null,
};
const writes = [];
const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  const json = (data, status = 200) => { res.writeHead(status, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(data)); };
  if (req.method !== 'GET') { writes.push({ method: req.method, path: url.pathname }); return json({ error: 'Unexpected write' }, 405); }
  if (url.pathname === '/api/jobs/search') return json({ items: [job], total: 1, all_total: 1, limit: 15, offset: 0 });
  if (url.pathname === '/api/jobs') return json([]);
  if (url.pathname === '/api/workbench') return json(workbench);
  if (url.pathname === '/api/history/unresolved-replies/count') return json({ count: 0 });
  if (url.pathname.startsWith('/api/')) return json({});
  if (url.pathname === '/favicon.ico') { res.writeHead(204); return res.end(); }
  try {
    const file = path.join(buildDir, !path.extname(url.pathname) ? 'index.html' : url.pathname);
    const type = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css' }[path.extname(file)] || 'application/octet-stream';
    const data = await fs.readFile(file);
    res.writeHead(200, { 'Content-Type': type }); res.end(data);
  } catch { res.writeHead(404); res.end('missing'); }
});

// A protocol fixture, not another application's implementation. Nothing is persisted.
const receiverHtml = `<!doctype html><html lang="zh"><title>合成本地接收页</title><body>
<h1>面试岗位草稿（仅测试）</h1><pre id="draft">等待交接</pre><script>
const source = new URL(location.href).searchParams.get('source');
window.receivedJobs = [];
window.sendReady = (version = 1) => window.opener.postMessage({ type: 'interview-sim:ready', version }, source);
window.addEventListener('message', event => {
  if (event.origin !== source || event.source !== window.opener || event.data?.type !== 'interview-sim:job') return;
  window.receivedJobs.push(event.data.job);
  document.querySelector('#draft').textContent = JSON.stringify(event.data.job);
  window.opener.postMessage({ type: 'interview-sim:received', version: 1 }, source);
});
</script></body></html>`;
const receiverServer = () => http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/html;charset=utf-8' }); res.end(receiverHtml);
});
const receiver = receiverServer();
const otherReceiver = receiverServer();
const servers = [server, receiver, otherReceiver];
const listen = service => new Promise(resolve => service.listen(0, '127.0.0.1', resolve));
const originOf = service => `http://127.0.0.1:${service.address().port}`;
const settle = page => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));

(async () => {
  await fs.mkdir(artifactDir, { recursive: true });
  await Promise.all(servers.map(listen));
  const origin = originOf(server);
  const target = originOf(receiver);
  const localhostTarget = `http://localhost:${receiver.address().port}`;
  const otherOrigin = originOf(otherReceiver);
  const allowed = new Set([origin, target, localhostTarget, otherOrigin]);
  const browser = await chromium.launch({ headless: true, channel: process.env.BROWSER_CHANNEL || 'chrome' });
  const errors = [];
  const externalRequests = [];
  const results = [];
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1100 }, acceptDownloads: true });
    context.on('page', page => {
      page.on('pageerror', error => errors.push(String(error)));
      page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    });
    await context.route('**/*', route => {
      const url = new URL(route.request().url());
      if (allowed.has(url.origin) || url.protocol === 'blob:') return route.continue();
      externalRequests.push(url.origin); return route.abort();
    });
    const page = await context.newPage();
    page.setDefaultTimeout(5000);
    const openPanel = async () => {
      await page.goto(`${origin}/jobs`);
      await page.getByRole('cell', { name: job.title, exact: true }).click();
      await page.getByRole('button', { name: '准备面试', exact: true }).click();
      return page.getByRole('region', { name: '面试准备', exact: true });
    };
    let panel = await openPanel();
    const send = () => panel.getByRole('button', { name: '打开并交接岗位', exact: true });
    const consent = () => panel.getByRole('checkbox');
    const address = () => panel.getByLabel('本地面试工作台地址');
    assert.equal(await send().isDisabled(), true, 'handoff must require consent');
    await panel.getByText('查看将交接的岗位内容', { exact: true }).click();
    assert.equal((await panel.locator('pre').innerText()).includes('PRIVATE_'), false);
    const downloadPromise = page.waitForEvent('download');
    await panel.getByRole('button', { name: '下载 JD（Markdown）', exact: true }).click();
    const download = await downloadPromise;
    assert.equal(download.suggestedFilename(), 'interview-job.md');
    const markdown = await fs.readFile(await download.path(), 'utf8');
    for (const value of Object.values(expectedJob)) assert.ok(markdown.includes(value));
    assert.equal(markdown.includes('PRIVATE_'), false, 'export must not include private extra fields');
    results.push('consent gate, preview and privacy-safe Markdown download');

    await address().fill(target);
    await consent().check();
    const popupPromise = page.waitForEvent('popup');
    await send().click();
    const popup = await popupPromise;
    await popup.waitForLoadState();
    const openedUrl = new URL(popup.url());
    assert.equal(openedUrl.origin, target);
    assert.deepEqual([...openedUrl.searchParams.keys()].sort(), ['import', 'source']);
    assert.equal(openedUrl.searchParams.get('source'), origin);
    assert.equal(openedUrl.searchParams.get('import'), 'job');
    assert.equal(decodeURIComponent(popup.url()).includes(job.title), false, 'JD must not be placed in the URL');
    await popup.evaluate(source => window.opener.postMessage({ type: 'interview-sim:received', version: 1 }, source), origin);
    await settle(page);
    assert.equal(await panel.getByRole('button', { name: '等待接收…', exact: true }).isDisabled(), true,
      'a receipt before any payload must not report success');

    // Same expected origin, but a different window cannot request the payload.
    const impostorPromise = page.waitForEvent('popup');
    await page.evaluate(url => window.open(url, '_blank'), openedUrl.href);
    const impostor = await impostorPromise;
    await impostor.waitForLoadState();
    await impostor.evaluate(() => window.sendReady());
    await settle(page);
    assert.deepEqual(await popup.evaluate(() => window.receivedJobs), []);
    assert.deepEqual(await impostor.evaluate(() => window.receivedJobs), []);
    assert.equal(await panel.getByRole('button', { name: '等待接收…', exact: true }).isDisabled(), true);

    // The correct window at a different origin must also be ignored.
    await popup.goto(`${otherOrigin}/?source=${encodeURIComponent(origin)}`);
    await popup.evaluate(() => window.sendReady());
    await settle(page);
    assert.deepEqual(await popup.evaluate(() => window.receivedJobs), []);
    await popup.goto(openedUrl.href);
    await popup.evaluate(() => window.sendReady(2));
    await settle(page);
    assert.deepEqual(await popup.evaluate(() => window.receivedJobs), []);
    await popup.evaluate(() => window.sendReady());
    await panel.getByRole('status').filter({ hasText: '岗位草稿已送达' }).waitFor();
    assert.deepEqual(await popup.evaluate(() => window.receivedJobs), [expectedJob]);
    await popup.evaluate(() => window.sendReady());
    await settle(page);
    assert.deepEqual(await popup.evaluate(() => window.receivedJobs), [expectedJob], 'one click sends only once');
    await popup.close(); await impostor.close();
    results.push('exact-origin/window/version handshake and one unsaved receiver draft');

    await address().fill(localhostTarget); await consent().check();
    const localhostPopupPromise = page.waitForEvent('popup');
    await send().click();
    const localhostPopup = await localhostPopupPromise;
    await localhostPopup.waitForLoadState();
    assert.equal(new URL(localhostPopup.url()).origin, localhostTarget);
    await localhostPopup.evaluate(() => window.sendReady());
    await panel.getByRole('status').filter({ hasText: '岗位草稿已送达' }).waitFor();
    assert.deepEqual(await localhostPopup.evaluate(() => window.receivedJobs), [expectedJob]);
    await localhostPopup.close();
    results.push('localhost hostname and 127.0.0.1 both work with exact target origins');

    let popupCount = 0;
    const countPopup = () => { popupCount += 1; };
    page.on('popup', countPopup);
    for (const invalid of ['https://example.invalid:8800', 'http://localhost:8800/path', origin, 'http://127.0.0.1:8800/?key=PRIVATE_API_KEY']) {
      await address().fill(invalid);
      assert.equal(await consent().isChecked(), false, 'changing target resets consent');
      await consent().check(); await send().click();
      await panel.getByRole('status').filter({ hasText: /只支持|不能是 BossHunter/ }).waitFor();
    }
    assert.equal(popupCount, 0, 'invalid targets must not open a tab');
    page.off('popup', countPopup);
    results.push('invalid/remote/self URLs rejected before opening a window');

    await address().fill(target); await consent().check();
    await page.evaluate(() => { window.originalOpenForTest = window.open; window.open = () => null; });
    await send().click();
    await panel.getByRole('status').filter({ hasText: '浏览器拦截了新标签页' }).waitFor();
    await page.evaluate(() => { window.open = window.originalOpenForTest; delete window.originalOpenForTest; });
    assert.equal(await send().isDisabled(), false);
    results.push('popup-blocked feedback and retry remain available');

    const stoppedPopupPromise = page.waitForEvent('popup');
    await send().click();
    const stoppedPopup = await stoppedPopupPromise;
    await stoppedPopup.waitForLoadState();
    await panel.getByRole('button', { name: '停止等待', exact: true }).click();
    await panel.getByRole('status').filter({ hasText: '已停止等待' }).waitFor();
    await stoppedPopup.evaluate(() => window.sendReady());
    await settle(page);
    assert.deepEqual(await stoppedPopup.evaluate(() => window.receivedJobs), [], 'cancelled handoff cannot subsequently send');
    assert.equal(stoppedPopup.isClosed(), false, 'cancel must preserve the opened tab');
    await stoppedPopup.close();
    results.push('stop waiting detaches the handshake and preserves the tab');

    // Use the browser's virtual clock, not a 15-second wall-clock sleep.
    await page.clock.install();
    const timeoutPopupPromise = page.waitForEvent('popup');
    await send().click();
    const timeoutPopup = await timeoutPopupPromise;
    await timeoutPopup.waitForLoadState();
    await page.clock.fastForward(15001);
    await panel.getByRole('status').filter({ hasText: '未收到接收确认' }).waitFor();
    await timeoutPopup.evaluate(() => window.sendReady());
    await page.clock.runFor(50);
    assert.deepEqual(await timeoutPopup.evaluate(() => window.receivedJobs), [], 'timeout must remove the listener');
    await timeoutPopup.close();
    results.push('15-second timeout exposes recovery and detaches the handshake');

    // Desktop and narrow desktop: the existing jobs table may horizontally scroll.
    for (const width of [1440, 1024, 768, 320]) {
      await page.setViewportSize({ width, height: 1100 });
      await panel.scrollIntoViewIfNeeded();
      const panelBox = await panel.boundingBox();
      assert.ok(panelBox && panelBox.x >= 0 && panelBox.x + panelBox.width <= width,
        `handoff content, including consent text, must fit the ${width}px viewport`);
      for (const control of [address(), consent(), send(), panel.getByRole('button', { name: '下载 JD（Markdown）', exact: true })]) {
        await control.scrollIntoViewIfNeeded();
        const box = await control.boundingBox();
        assert.ok(box && box.width > 0 && box.height > 0, `control must be rendered at ${width}px`);
        assert.ok(box.x < width && box.x + box.width > 0, `control must be reachable at ${width}px`);
      }
      await send().scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(artifactDir, `interview-handoff-${width}.png`) });
    }
    results.push('handoff panel and essential controls fit at 1440px, 1024px, 768px and 320px');
    assert.deepEqual(writes, [], 'handoff must not mutate BossHunter jobs or start a task');
    assert.deepEqual(externalRequests, [], 'tests may not request any external origin');
    assert.deepEqual(errors, [], 'all pages must have no runtime or console errors');
    const report = { results, pageErrors: errors, externalRequests, writes, allData: 'synthetic, isolated local HTTP only' };
    await fs.writeFile(path.join(artifactDir, 'interview-handoff-results.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
    await Promise.all(servers.map(service => new Promise(resolve => service.close(resolve))));
  }
})().catch(error => {
  console.error(error); process.exitCode = 1; servers.forEach(service => service.close());
});
