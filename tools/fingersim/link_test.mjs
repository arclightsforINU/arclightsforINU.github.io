// Drives finger-led/app/serial-link.js against a fake Web Serial port.
// Run: node link_test.mjs
import fs from 'node:fs';
import vm from 'node:vm';

const tick = (ms = 0) => new Promise(r => setTimeout(r, ms));

// A port whose writes take `writeMs` each (9600 baud: about 1 ms per byte) and whose
// readable can be fed, errored (non-fatal: a new stream replaces it) or unplugged.
function fakePort(writeMs = 10) {
  const port = { written: [], closed: false, inFlight: 0, maxInFlight: 0 };
  let controller;
  const newReadable = () => new ReadableStream({ start: c => { controller = c; } });
  let readable = newReadable();
  Object.defineProperty(port, 'readable', { get: () => readable });
  port.writable = new WritableStream({
    async write(chunk) {
      port.maxInFlight = Math.max(port.maxInFlight, ++port.inFlight);
      await tick(writeMs);
      port.written.push(new TextDecoder().decode(chunk));
      port.inFlight--;
    },
  });
  port.open = async () => {};
  port.close = async () => { port.closed = true; };
  port.feed = text => controller.enqueue(new TextEncoder().encode(text));
  port.glitch = () => { const old = controller; readable = newReadable(); old.error(new Error('framing')); };
  port.unplug = () => { const old = controller; readable = null; old.error(new Error('lost')); };
  return port;
}

const ctx = vm.createContext({ TextEncoder, TextDecoder, navigator: {} });
vm.runInContext(fs.readFileSync(new URL('../../finger-led/app/serial-link.js', import.meta.url), 'utf8'), ctx);
const SerialLink = vm.runInContext('SerialLink', ctx);

let ok = true;
function expect(name, pass, detail = '') {
  console.log(`${name.padEnd(58)} ${pass ? 'PASS' : 'FAIL'} ${detail}`);
  ok &&= pass;
}

async function openLink(port) {
  const lines = [];
  let closes = 0;
  ctx.navigator.serial = { requestPort: async () => port };
  const link = new SerialLink(9600, line => lines.push(line), () => closes++);
  await link.open();
  return { link, lines, closes: () => closes };
}

{
  const port = fakePort();
  const { link } = await openLink(port);
  for (let level = 1; level <= 50; level++) link.sendLatest('LEVEL:' + level);
  await tick(60);
  expect('burst of 50 levels -> first and newest only', JSON.stringify(port.written) === '["LEVEL:1\\n","LEVEL:50\\n"]',
    JSON.stringify(port.written));
  expect('never more than one write in flight', port.maxInFlight === 1);
  await link.close();
}
{
  const port = fakePort(1);
  const { link } = await openLink(port);
  for (let level = 0; level < 20; level++) { link.sendLatest('LEVEL:' + level); await tick(5); }
  await tick(20);
  expect('slow changes -> every level sent in order', port.written.length === 20 && port.written[19] === 'LEVEL:19\n');
  await link.close();
}
{
  const port = fakePort();
  const { link, lines } = await openLink(port);
  port.feed('REA'); port.feed('DY\r\nPWM:4'); port.feed('7\r\n\r\n');
  await tick(5);
  expect('lines split across chunks are rejoined and trimmed', JSON.stringify(lines) === '["READY","PWM:47"]', JSON.stringify(lines));
  port.glitch();
  await tick(5);
  port.feed('PWM:9\n');
  await tick(5);
  expect('read error that replaces the stream: reading resumes', lines.at(-1) === 'PWM:9' && link.isOpen);
  await link.close();
}
{
  const port = fakePort();
  const { link, closes } = await openLink(port);
  link.sendLatest('LEVEL:3');
  port.unplug();
  await tick(30);
  expect('unplug: link closes itself once', !link.isOpen && closes() === 1 && port.closed);
  link.sendLatest('LEVEL:4');
  await tick(20);
  expect('send after close is ignored', !port.written.includes('LEVEL:4\n'));
}
{
  const port = fakePort();
  const { link, closes } = await openLink(port);
  link.sendLatest('LEVEL:1');
  link.sendLatest('LEVEL:2');
  await link.close();
  expect('close waits for the write in flight, drops the pending one',
    JSON.stringify(port.written) === '["LEVEL:1\\n"]' && closes() === 1 && port.closed && !port.writable.locked);
  await link.close();
  expect('second close does nothing', closes() === 1);
}

console.log(ok ? 'ALL PASS' : 'SOME FAILED');
process.exit(ok ? 0 : 1);
