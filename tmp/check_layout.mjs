import fs from 'node:fs/promises';
import path from 'node:path';

const dir = 'C:/Users/dudal/.codex/visualizations/2026/07/11/019f5086-6f58-7df2-8731-0398dd974bae/codex-presentations/manual-smart-fridge-design/tmp/layout';
const files = (await fs.readdir(dir)).filter((name) => name.endsWith('.layout.json')).sort();
const problems = [];

function visit(value, trail, slide) {
  if (!value || typeof value !== 'object') return;
  if (Array.isArray(value.bbox) && value.bbox.length === 4 && value.bbox.every(Number.isFinite)) {
    const [x, y, w, h] = value.bbox;
    if (x < -0.01 || y < -0.01 || x + w > 1400.01 || y + h > 990.01) {
      problems.push({ slide, trail, bbox: value.bbox, kind: value.kind, id: value.id });
    }
  }
  for (const [key, child] of Object.entries(value)) {
    if (key !== 'bbox') visit(child, `${trail}.${key}`, slide);
  }
}

for (const file of files) {
  const doc = JSON.parse(await fs.readFile(path.join(dir, file), 'utf8'));
  visit(doc, '$', doc.slide?.slide ?? file);
}

console.log(JSON.stringify({ slideCount: files.length, overflowCount: problems.length, problems }, null, 2));
