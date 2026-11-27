import * as vscode from 'vscode';

const BACKEND = 'http://localhost:5001';
let lastFix = '';
let lastId = '';

function html(): string {
  return `<body style="font-family:sans-serif">
<select id="mode">
  <option value="explain">Explain</option>
  <option value="debug">Debug</option>
  <option value="fix">Fix</option>
  <option value="tests">Unit tests</option>
  <option value="improve">Improve</option>
</select>
<button id="go">Run on selection</button>
<button id="apply" hidden>Review and apply</button>
<pre id="out" style="white-space:pre-wrap"></pre>
<div id="fb" hidden><button id="up">👍</button> <button id="down">👎</button></div>
<script>
const vs = acquireVsCodeApi();
go.onclick = () => { out.textContent = 'Thinking...'; vs.postMessage({ type: 'ask', mode: mode.value }); };
apply.onclick = () => vs.postMessage({ type: 'apply' });
up.onclick = () => vs.postMessage({ type: 'vote', vote: 'up' });
down.onclick = () => vs.postMessage({ type: 'vote', vote: 'down' });
addEventListener('message', e => { out.textContent = e.data.text; apply.hidden = e.data.mode !== 'fix'; fb.hidden = !e.data.id; });
</script></body>`;
}

async function post(path: string, body: object): Promise<any> {
  const r = await fetch(BACKEND + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data: any = await r.json();
  if (!r.ok) { throw new Error(data.error); }
  return data;
}

async function ask(view: vscode.WebviewView, mode: string) {
  const ed = vscode.window.activeTextEditor;
  if (!ed) {
    view.webview.postMessage({ text: 'Open a file first.' });
    return;
  }
  const code = ed.document.getText(ed.selection) || ed.document.getText();
  const errors = vscode.languages
    .getDiagnostics(ed.document.uri)
    .filter(d => d.severity === vscode.DiagnosticSeverity.Error)
    .map(d => 'Line ' + (d.range.start.line + 1) + ': ' + d.message)
    .join('\n');
  try {
    const data = await post('/analyze', { mode, code, error: errors });
    if (mode === 'fix') { lastFix = data.result; }
    lastId = data.id || '';
    view.webview.postMessage({ text: data.result, mode, id: data.id });
  } catch (e: any) {
    view.webview.postMessage({ text: 'Error: ' + e.message });
  }
}

async function apply() {
  const ed = vscode.window.activeTextEditor;
  if (!ed || !lastFix) { return; }
  const fixedDoc = await vscode.workspace.openTextDocument({ content: lastFix, language: 'python' });
  await vscode.commands.executeCommand('vscode.diff', ed.document.uri, fixedDoc.uri, 'DevPilot: review fix');
  const pick = await vscode.window.showInformationMessage('Apply this fix?', 'Apply', 'Cancel');
  if (pick === 'Apply') {
    const range = ed.selection.isEmpty
      ? ed.document.validateRange(new vscode.Range(0, 0, 1000000, 0))
      : ed.selection;
    await ed.edit(b => b.replace(range, lastFix));
  }
}

async function vote(v: string) {
  if (!lastId) { return; }
  await post('/feedback', { id: lastId, vote: v });
  vscode.window.showInformationMessage('Thanks for your feedback!');
}

class Provider implements vscode.WebviewViewProvider {
  resolveWebviewView(view: vscode.WebviewView) {
    view.webview.options = { enableScripts: true };
    view.webview.html = html();
    view.webview.onDidReceiveMessage((m) => {
      if (m.type === 'ask') { ask(view, m.mode); }
      if (m.type === 'apply') { apply(); }
      if (m.type === 'vote') { vote(m.vote); }
    });
  }
}

export function activate(ctx: vscode.ExtensionContext) {
  ctx.subscriptions.push(
    vscode.window.registerWebviewViewProvider('devpilot.chat', new Provider())
  );
}
export function deactivate() {}