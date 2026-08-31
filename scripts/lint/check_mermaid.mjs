// Parse every ```mermaid block the way github.com does.
//
// This exists because of a bug that shipped: the diagrams validated locally and rendered as
// broken boxes on GitHub. Mermaid's own default is htmlLabels:true, GitHub's is false, so
// <i>/<b>/<code> inside a node label parsed fine here and failed there. Validating under the
// library default is not validation — it has to match the renderer that people actually see.
//
//   npm i mermaid@11 jsdom && node scripts/lint/check_mermaid.mjs .
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!DOCTYPE html><body></body>', { pretendToBeVisual: true });
global.window = dom.window;
global.document = dom.window.document;
Object.defineProperty(global, 'navigator', { value: dom.window.navigator, configurable: true });

const mermaid = (await import('mermaid')).default;
mermaid.initialize({
  startOnLoad: false,
  securityLevel: 'strict',
  htmlLabels: false,              // GitHub's setting, not mermaid's default
  flowchart: { htmlLabels: false },
  theme: 'default',
});

const root = process.argv[2] ?? '.';
const walk = (d) => readdirSync(d).flatMap((f) => {
  if (f === '.git' || f === 'node_modules') return [];
  const p = join(d, f);
  return statSync(p).isDirectory() ? walk(p) : (p.endsWith('.md') ? [p] : []);
});

let checked = 0, failed = 0;
for (const file of walk(root)) {
  const src = readFileSync(file, 'utf8');
  for (const [i, m] of [...src.matchAll(/```mermaid\n([\s\S]*?)```/g)].entries()) {
    checked++;
    const body = m[1];
    // Cheap checks first: they give a better message than the parser's line number.
    const html = [...body.matchAll(/<\/?([a-zA-Z]+)[^>]*>/g)].map((x) => x[1])
                   .filter((t) => t.toLowerCase() !== 'br');
    if (html.length) {
      failed++;
      console.log(`FAIL ${file} #${i + 1}: <${html[0]}> in a node label — GitHub runs `
                + `htmlLabels:false, so only <br/> survives. Drop the tag.`);
      continue;
    }
    try {
      await mermaid.parse(body);
    } catch (e) {
      failed++;
      const first = String(e.message).split('\n')[0];
      console.log(`FAIL ${file} #${i + 1}: ${first}`);
      console.log(`     tip: a label containing ( ) , : ; # & % must be quoted — id["like this"]`);
    }
  }
}
console.log(`\n${checked} mermaid diagrams checked, ${failed} failed`);
process.exit(failed ? 1 : 0);
