with open('C:/Users/Palak Vardhan/dashboard/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Fix loadFromCloud to not silently fail with {}
old_load = """async function loadFromCloud() {
  if (!JSONBIN_BIN_ID) return {};
  try {
    const res = await fetch(`${API_BASE}/${JSONBIN_BIN_ID}/latest`, { headers: { 'X-Master-Key': JSONBIN_KEY } });
    const data = await res.json();
    const rec = data.record || {};
    delete rec.initialized;
    return rec;
  } catch { return {}; }
}"""

new_load = """async function loadFromCloud() {
  if (!JSONBIN_BIN_ID) return null;
  try {
    const res = await fetch(`${API_BASE}/${JSONBIN_BIN_ID}/latest`, { headers: { 'X-Master-Key': JSONBIN_KEY } });
    if (!res.ok) { console.warn('[PSAT Sync] Fetch failed:', res.status); return null; }
    const data = await res.json();
    const rec = data.record || {};
    delete rec.initialized;
    console.log('[PSAT Sync] Loaded from cloud, keys:', Object.keys(rec).length);
    return rec;
  } catch(e) { console.error('[PSAT Sync] Error:', e); return null; }
}"""

# Fix pollCloud to not overwrite state on failed fetch
old_poll = """async function pollCloud() {
  if (!JSONBIN_BIN_ID) return;
  setSyncStatus('polling');
  const fresh = await loadFromCloud();
  const freshStr = JSON.stringify(fresh);
  if (freshStr !== lastPollData) {
    lastPollData = freshStr;
    psatState = fresh;
    buildPsatTable();
    updateKPIs();
  }
  setSyncStatus('saved');
}"""

new_poll = """async function pollCloud() {
  if (!JSONBIN_BIN_ID) return;
  setSyncStatus('polling');
  const fresh = await loadFromCloud();
  if (fresh === null) { setSyncStatus('error'); return; } // don't overwrite on fetch failure
  const freshStr = JSON.stringify(fresh);
  if (freshStr !== lastPollData) {
    console.log('[PSAT Sync] Detected remote changes, updating table...');
    lastPollData = freshStr;
    // Preserve local __history__ if remote doesn't have it yet
    const localHist = psatState['__history__'];
    psatState = fresh;
    if (!psatState['__history__'] && localHist) psatState['__history__'] = localHist;
    buildPsatTable();
    updateKPIs();
  }
  setSyncStatus('saved');
}"""

c = c.replace(old_load, new_load)
c = c.replace(old_poll, new_poll)

print('loadFromCloud fixed:', 'return null' in c)
print('pollCloud fixed:', 'fetch failure' in c)

with open('C:/Users/Palak Vardhan/dashboard/index.html', 'w', encoding='utf-8') as f:
    f.write(c)
print('done')
