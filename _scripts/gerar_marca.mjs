// Gera os PNGs da marca do Freedom a partir de assets/freedom/logo.svg:
// os ícones quadrados e a imagem de compartilhamento.
//
//   npm i playwright @fontsource/roboto
//   node _scripts/gerar_marca.mjs
//
// A Roboto entra embutida em base64 para a imagem não depender de fonte
// instalada na máquina nem do Google Fonts; sem o pacote, cai na fonte do
// sistema e a imagem sai com outro desenho de letra.
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const RAIZ = path.join(path.dirname(fileURLToPath(import.meta.url)),
                       '..', 'assets', 'freedom');

const FONTES = ['400', '700'].map(peso => {
  const arquivo = `node_modules/@fontsource/roboto/files/roboto-latin-${peso}-normal.woff2`;
  if (!fs.existsSync(arquivo)) { return ''; }
  return `@font-face{font-family:Roboto;font-weight:${peso};
    src:url(data:font/woff2;base64,${fs.readFileSync(arquivo, 'base64')}) format('woff2')}`;
}).join('\n');
const svg = fs.readFileSync(RAIZ + '/logo.svg', 'utf8');
const browser = await chromium.launch(process.env.PLAYWRIGHT_CHROMIUM
  ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM } : {});

// ícones quadrados a partir do mesmo SVG
async function icone(lado, arquivo, raio) {
  const page = await browser.newPage({ viewport: { width: lado, height: lado } });
  const corpo = raio === undefined ? svg : svg.replace('rx="12"', `rx="${raio}"`);
  await page.setContent(`<body style="margin:0">
    <div style="width:${lado}px;height:${lado}px">
      ${corpo.replace('width="56" height="56"', `width="${lado}" height="${lado}"`)}
    </div></body>`);
  await page.screenshot({ path: `${RAIZ}/${arquivo}`, omitBackground: true });
  await page.close();
}

await icone(180, 'icone-180.png', 0);   // apple-touch-icon: o iOS já arredonda
await icone(512, 'icone-512.png');

// imagem de compartilhamento: fundo claro, como o site
const og = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await og.setContent(`<!doctype html><html><head>
  <style>${FONTES}</style>
  </head><body style="margin:0;width:1200px;height:630px;background:#f7f9fc;
    font-family:Roboto,system-ui,sans-serif;color:#1b2a4a;display:flex;flex-direction:column;
    justify-content:center;padding:0 92px;box-sizing:border-box;
    border-bottom:14px solid #1b2a4a">
  <div style="display:flex;align-items:center;gap:26px">
    ${svg.replace('width="56" height="56"', 'width="104" height="104"')}
    <div style="font-size:76px;font-weight:700;letter-spacing:-1.6px">Freedom</div>
  </div>
  <div style="font-size:36px;line-height:1.35;margin-top:36px;max-width:1000px;color:#23324a">
    Empresa boa é a que lucra, cresce e não vive de dívida.
  </div>
  <div style="font-size:26px;margin-top:20px;color:#5b6672">
    2.383 empresas da B3, NYSE e NASDAQ · 11 anos de balanço
  </div>
  <div style="position:absolute;left:92px;bottom:58px;font-size:22px;color:#7b8794">
    yurisilva.com.br/apps/freedom
  </div>
</body></html>`);
await og.waitForTimeout(1200);
await og.screenshot({ path: `${RAIZ}/og.png` });
await og.close();

await browser.close();
console.log('marca gerada em', RAIZ);
