// HCA -> 16-bit WAV for tools/xv2acb.py's extracted files, through hca.js (a port of VGAudio / vgmstream's HCA
// decoder; `npm i --ignore-scripts hca.js` into HCA_JS_DIR).
//   node tools/xv2acb_decode.mjs HCA_JS_DIR IN_DIR OUT_DIR
import fs from 'fs';
import path from 'path';
import { pathToFileURL } from 'url';

const [,, hcaDir, inDir, outDir] = process.argv;
if (!outDir) {
  console.log('node tools/xv2acb_decode.mjs HCA_JS_DIR IN_DIR OUT_DIR');
  process.exit(1);
}
const { default: HCA } = await import(pathToFileURL(path.join(hcaDir, 'node_modules/hca.js/dst/hca.js')).href);
fs.mkdirSync(outDir, { recursive: true });
let bad = 0;
for (const f of fs.readdirSync(inDir).sort()) {
  if (!f.endsWith('.hca')) continue;
  try {
    const hca = new Uint8Array(fs.readFileSync(path.join(inDir, f)));
    const wav = HCA.decode(HCA.decrypt(hca.slice(0), 'nokey'), 16);
    fs.writeFileSync(path.join(outDir, f.replace(/\.hca$/, '.wav')), wav);
    console.log(f, '->', f.replace(/\.hca$/, '.wav'));
  } catch (e) {
    bad++;
    console.log('FAIL', f, String(e).slice(0, 200));
  }
}
process.exit(bad ? 1 : 0);
