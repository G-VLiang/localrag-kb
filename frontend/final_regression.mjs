import { chromium } from 'playwright';
const results = [];
const log = (s, ok, d='') => { results.push(ok); console.log(`${ok?'✅':'❌'} ${s}${d?' — '+d:''}`); };

const browser = await chromium.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  headless: true,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on('pageerror', e => errors.push(e.message));
let dialogResponse = '';
page.on('dialog', async d => { await d.accept(dialogResponse); });

const email = 'reg_' + Date.now() + '@test.com';
try {
  // 注册
  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await page.click('text=去注册');
  await page.waitForTimeout(500);
  await page.fill('input[type=email]', email);
  await page.fill('input[type=text]', '回归测试');
  await page.fill('input[type=password]', 'test123456');
  await page.click('button[type=submit]');
  await page.waitForTimeout(1500);
  log('注册', (await page.locator('body').innerText()).includes('去登录'));

  // 登录
  await page.fill('input[type=email]', email);
  await page.fill('input[type=password]', 'test123456');
  await page.click('button[type=submit]');
  await page.waitForTimeout(2000);
  log('登录', page.url() === 'http://localhost:5173/');

  // 自动空间
  log('自动建空间', (await page.locator('body').innerText()).includes('的空间'));

  // 进空间 + 建知识库 + 建文档
  await page.locator('button', { hasText: '的空间' }).first().click();
  await page.waitForTimeout(2000);
  dialogResponse = '回归知识库';
  await page.click('text=+ 新建');
  await page.waitForTimeout(1500);
  log('建知识库', (await page.locator('body').innerText()).includes('回归知识库'));

  dialogResponse = '回归文档';
  await page.click('text=+ 文档');
  await page.waitForTimeout(2000);
  log('建文档', (await page.locator('body').innerText()).includes('回归文档'));

  // 编辑 + 保存
  const editor = page.locator('.ProseMirror');
  await editor.click();
  await page.keyboard.type('回归测试正文内容123');
  await page.waitForTimeout(500);
  await page.click('button:has-text("保存")');
  await page.waitForTimeout(2000);
  log('保存', !(await page.locator('body').innerText()).includes('未保存'));

  // 刷新持久化
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  log('刷新保持登录', page.url() === 'http://localhost:5173/space/');
  log('文档持久化', (await page.locator('body').innerText()).includes('回归文档'));

  // 智能问答切换
  await page.click('text=回归文档');
  await page.waitForTimeout(1500);
  await page.click('text=智能问答');
  await page.waitForTimeout(1000);
  log('切换智能问答', (await page.locator('body').innerText()).includes('就你的知识库提问'));

  await page.screenshot({ path: 'regression_final.png' });
} catch (e) {
  console.log('❌ 异常:', e.message);
  await page.screenshot({ path: 'regression_error.png' }).catch(()=>{});
}

console.log('\n=== 错误 ===');
errors.forEach(e => console.log(e.slice(0,200)));
console.log(`\n=== 通过 ${results.filter(Boolean).length}/${results.length} ===`);
await browser.close();
