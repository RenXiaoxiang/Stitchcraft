/* Stitchcraft front-end config module.
   Constants shared by the studio shell; loaded before app.js (no build step). */
(function () {
  'use strict';

  const STAGES = [
    { key: 'brief', label: 'Brief' }, { key: 'structure', label: 'Structure' }, { key: 'design', label: 'Design tokens' },
    { key: 'data', label: 'Data layer' }, { key: 'layout', label: 'Hero & layout' }, { key: 'components', label: 'Components' },
    { key: 'motion', label: 'Motion' }, { key: 'a11y', label: 'Accessibility' }, { key: 'qa', label: 'QA & package' } ];
  const PRESETS = {
    pollinations: { base_url: 'https://text.pollinations.ai/openai', model: 'openai', label: 'Pollinations (free)', requires_key: false, kind: 'free-keyless', note: 'Free community endpoint, no API key needed. Free tier allows about one request per 30s and short output — good for a first try.', key_url: '' },
    ollama: { base_url: 'http://127.0.0.1:11434/v1', model: 'llama3.1', label: 'Ollama (local)', requires_key: false, kind: 'local', note: 'Runs on this machine. Install Ollama, run `ollama serve`, then pull a model.', key_url: 'https://ollama.com/download' },
    zhipu: { base_url: 'https://open.bigmodel.cn/api/paas/v4/', model: 'glm-4-flash', label: '智谱 GLM-4-Flash (free)', requires_key: true, kind: 'free-key', note: '国内可直连；glm-4-flash 永久免费，注册后创建免费 Key。', key_url: 'https://open.bigmodel.cn/' },
    siliconflow: { base_url: 'https://api.siliconflow.cn/v1', model: 'THUDM/GLM-Z1-9B-0414', label: 'SiliconFlow 免费模型', requires_key: true, kind: 'free-key', note: '国内可直连；部分小模型 0 元，注册免费 Key，模型名以控制台为准。', key_url: 'https://cloud.siliconflow.cn/' },
    groq: { base_url: 'https://api.groq.com/openai/v1', model: 'llama-3.3-70b-versatile', label: 'Groq (free tier)', requires_key: true, kind: 'free-key', note: 'Free tier with a free API key from console.groq.com.', key_url: 'https://console.groq.com/keys' },
    gemini: { base_url: 'https://generativelanguage.googleapis.com/v1beta/openai/', model: 'gemini-2.5-flash', label: 'Google Gemini (free tier)', requires_key: true, kind: 'free-key', note: 'Free tier with a Google AI Studio key.', key_url: 'https://aistudio.google.com/apikey' },
    openrouter: { base_url: 'https://openrouter.ai/api/v1', model: 'meta-llama/llama-3.3-70b-instruct:free', label: 'OpenRouter (free models)', requires_key: true, kind: 'free-pool', note: 'Free models end with ":free" — type the exact id in the Model field.', key_url: 'https://openrouter.ai/keys' },
    github: { base_url: 'https://models.github.ai/inference', model: 'openai/gpt-4o-mini', label: 'GitHub Models (free)', requires_key: true, kind: 'free-key', note: 'Free quota with your GitHub account: create a PAT with the "models: read" scope.', key_url: 'https://github.com/settings/tokens' },
    openai: { base_url: 'https://api.openai.com/v1', model: 'gpt-4o-mini', label: 'OpenAI (paid)', requires_key: true, kind: 'paid', note: 'Requires a paid OpenAI API key.', key_url: 'https://platform.openai.com/api-keys' },
    deepseek: { base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat', label: 'DeepSeek (paid)', requires_key: true, kind: 'paid', note: 'DeepSeek\'s official API is paid; use a free provider for zero-cost runs.', key_url: 'https://platform.deepseek.com/' },
    custom: { base_url: '', model: '', label: 'Custom', requires_key: false, kind: 'custom', note: 'Any OpenAI-compatible endpoint. Leave the key blank for local or keyless servers.', key_url: '' } };
  /* Mirrors themes/registry.toml so the catalogue still renders offline. */
  const FALLBACK_THEMES = [
    { id: 'warehouse-ops', name: 'Warehouse Operations', category: 'data', accent: '#ff8a3d', has_sample: true, tags: ['inventory', 'dashboard', 'crud', 'operations'], summary: 'An inventory command center: live stock, inbound shipments, low-stock alerts and one-click item updates.' },
    { id: 'personal-space', name: 'Personal Space', category: 'personal', accent: '#c9a86a', has_sample: true, tags: ['personal', 'writing', 'gallery'], summary: 'A quiet home for essays, field notes and photographs, made for writers and makers with a literary pulse.' },
    { id: 'staff-directory', name: 'Staff Directory', category: 'data', accent: '#b6f24a', has_sample: true, tags: ['people', 'directory', 'crud'], summary: 'A people-first directory: searchable employee cards, department groupings and onboarding checklists.' },
    { id: 'logistics-control', name: 'Logistics Control', category: 'data', accent: '#38d6e0', has_sample: true, tags: ['logistics', 'tracking', 'incidents'], summary: 'A midnight-blue operations console for shipment tracking, carrier performance and incident response.' },
    { id: 'brand-launch', name: 'Brand Launch', category: 'brand', accent: '#ff4d1f', has_sample: true, tags: ['brand', 'landing', 'editorial'], summary: 'A high-contrast editorial landing page: manifesto-led storytelling, launch timeline and one conversion band.' } ];
  const STORAGE = { theme: 'stitchcraft.theme', title: 'stitchcraft.title' };
  const POLL_MS = 800, MAX_POLL_FAILS = 4, STEP_COUNT = 5;
  const DONE = ['done', 'complete', 'completed', 'success', 'succeeded', 'finished', 'ok'];
  const CANCELLED = ['cancelled', 'canceled'];
  const FAIL = ['error', 'failed', 'failure', 'timeout'];
  const STAGE_STATUS = {
    active: 'active', running: 'active', in_progress: 'active', 'in-progress': 'active', current: 'active', started: 'active', working: 'active',
    done: 'done', complete: 'done', completed: 'done', ok: 'done', success: 'done', succeeded: 'done', passed: 'done', skipped: 'done',
    error: 'error', failed: 'error', failure: 'error', cancelled: 'error', canceled: 'error', timeout: 'error' };
  const LOG_LEVEL = {
    warn: 'warn', warning: 'warn', error: 'error', err: 'error', fail: 'error', failed: 'error', critical: 'error', fatal: 'error',
    success: 'success', done: 'success', ok: 'success', complete: 'success', completed: 'success', passed: 'success',
    debug: 'debug', trace: 'debug', active: 'active', progress: 'active', running: 'active', start: 'active', started: 'active' };

  window.StitchcraftConfig = {
    STAGES: STAGES, PRESETS: PRESETS, FALLBACK_THEMES: FALLBACK_THEMES, STORAGE: STORAGE,
    POLL_MS: POLL_MS, MAX_POLL_FAILS: MAX_POLL_FAILS, STEP_COUNT: STEP_COUNT,
    DONE: DONE, CANCELLED: CANCELLED, FAIL: FAIL, STAGE_STATUS: STAGE_STATUS, LOG_LEVEL: LOG_LEVEL
  };
})();
