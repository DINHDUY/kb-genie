#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const errors = [];

function fail(message) {
  errors.push(message);
}

function readJson(rel) {
  const full = path.join(root, rel);
  if (!fs.existsSync(full)) {
    fail(`Missing ${rel}`);
    return null;
  }
  try {
    return JSON.parse(fs.readFileSync(full, 'utf8'));
  } catch (err) {
    fail(`Invalid JSON in ${rel}: ${err.message}`);
    return null;
  }
}

function parseFrontmatter(filePath) {
  const text = fs.readFileSync(filePath, 'utf8').replace(/\r\n/g, '\n');
  if (!text.startsWith('---\n')) {
    return null;
  }
  const end = text.indexOf('\n---\n', 4);
  if (end === -1) return null;
  const block = text.slice(4, end);
  const data = {};
  for (const line of block.split('\n')) {
    const match = line.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (!match) continue;
    data[match[1]] = match[2].replace(/^["']|["']$/g, '').trim();
  }
  return data;
}

function walkMarkdown(dir, extensions) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walkMarkdown(full, extensions));
      continue;
    }
    if (extensions.some((ext) => entry.name.endsWith(ext))) {
      out.push(full);
    }
  }
  return out;
}

function isSafeRelativePath(value) {
  if (typeof value !== 'string' || value.length === 0) return false;
  if (value.startsWith('http://') || value.startsWith('https://')) return true;
  if (path.isAbsolute(value)) return false;
  const normalized = path.posix.normalize(value.replace(/\\/g, '/'));
  return !normalized.startsWith('../') && normalized !== '..';
}

function assertRelativeSafe(value, label) {
  if (typeof value !== 'string') return;
  if (!isSafeRelativePath(value)) {
    fail(`${label} must be a relative path without '..': ${value}`);
  }
}

function extractPathValues(value) {
  if (typeof value === 'string') return [value];
  if (Array.isArray(value)) return value.flatMap((entry) => extractPathValues(entry));
  return [];
}

const kebab = /^[a-z0-9]+(?:[.-][a-z0-9]+)*$/;
const kebabStrict = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const marketplaceName = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/;

const marketplace = readJson('.cursor-plugin/marketplace.json');
if (!marketplace) {
  summarizeAndExit();
}

if (typeof marketplace.name !== 'string' || !marketplaceName.test(marketplace.name)) {
  fail('marketplace.json name must be lowercase kebab-case');
}
if (!marketplace.owner || typeof marketplace.owner !== 'object' || !marketplace.owner.name) {
  fail('marketplace.json owner.name is required');
}
if (!Array.isArray(marketplace.plugins) || marketplace.plugins.length === 0) {
  fail('marketplace.json plugins must be a non-empty array');
  summarizeAndExit();
}

const seenNames = new Set();
let agentFiles = [];
let skillDirs = [];
let commandFiles = [];
let ruleFiles = [];

for (const [index, entry] of marketplace.plugins.entries()) {
  const label = `plugins[${index}]`;
  if (!entry || typeof entry !== 'object') {
    fail(`${label} must be an object`);
    continue;
  }
  if (typeof entry.name !== 'string' || !kebab.test(entry.name)) {
    fail(`${label}.name must be lowercase kebab-case`);
    continue;
  }
  if (seenNames.has(entry.name)) {
    fail(`Duplicate plugin name in marketplace: ${entry.name}`);
  }
  seenNames.add(entry.name);

  if (typeof entry.source !== 'string' || !isSafeRelativePath(entry.source)) {
    fail(`${label}.source must be a safe relative path`);
    continue;
  }

  const pluginDir = path.join(root, entry.source);
  if (!fs.existsSync(pluginDir) || !fs.statSync(pluginDir).isDirectory()) {
    fail(`${label}.source directory missing: ${entry.source}`);
    continue;
  }

  const manifestRel = path.join(entry.source, '.cursor-plugin/plugin.json');
  const manifest = readJson(manifestRel);
  if (!manifest) continue;

  if (!manifest.name || !kebab.test(manifest.name)) {
    fail(`${entry.name}: plugin.json name must be lowercase kebab-case`);
  }
  if (manifest.name && manifest.name !== entry.name) {
    fail(`${entry.name}: marketplace entry name does not match plugin.json name (${manifest.name})`);
  }
  if (!manifest.displayName) fail(`${entry.name}: plugin.json missing displayName`);
  if (!manifest.description) fail(`${entry.name}: plugin.json missing description`);
  if (!manifest.version) fail(`${entry.name}: plugin.json missing version`);
  if (!manifest.author || typeof manifest.author !== 'object' || !manifest.author.name) {
    fail(`${entry.name}: plugin.json author must be an object with name`);
  }
  if (manifest.servers) fail(`${entry.name}: plugin.json must not use undocumented servers field`);
  if (Array.isArray(manifest.skills) && manifest.skills.some((s) => s && typeof s === 'object' && 'prompt' in s)) {
    fail(`${entry.name}: plugin.json skills must be paths, not inline prompt objects`);
  }

  for (const field of ['logo', 'agents', 'skills', 'rules', 'commands']) {
    for (const p of extractPathValues(manifest[field])) {
      assertRelativeSafe(p, `${entry.name} ${field}`);
      if (p.startsWith('http://') || p.startsWith('https://')) continue;
      if (!fs.existsSync(path.join(pluginDir, p))) {
        fail(`${entry.name}: declared ${field} path missing: ${p}`);
      }
    }
  }

  const pluginSkills = fs.existsSync(path.join(pluginDir, 'skills'))
    ? fs.readdirSync(path.join(pluginDir, 'skills'), { withFileTypes: true }).filter((e) => e.isDirectory())
    : [];
  if (pluginSkills.length === 0) fail(`${entry.name}: no skills found under skills/*/SKILL.md`);
  for (const dir of pluginSkills) {
    const skillFile = path.join(pluginDir, 'skills', dir.name, 'SKILL.md');
    const rel = path.relative(root, skillFile);
    if (!fs.existsSync(skillFile)) {
      fail(`Missing ${rel}`);
      continue;
    }
    const fm = parseFrontmatter(skillFile);
    if (!fm || !fm.name || !fm.description) {
      fail(`${rel} needs name and description frontmatter`);
    } else if (!kebabStrict.test(fm.name)) {
      fail(`Skill name must be kebab-case: ${fm.name}`);
    }
  }

  const pluginAgents = walkMarkdown(path.join(pluginDir, 'agents'), ['.md', '.mdc', '.markdown']);
  if (pluginAgents.length === 0) fail(`${entry.name}: no agent files found under agents/`);
  for (const file of pluginAgents) {
    const fm = parseFrontmatter(file);
    const rel = path.relative(root, file);
    if (!fm || !fm.name || !fm.description) {
      fail(`${rel} needs name and description frontmatter`);
    } else if (!kebabStrict.test(fm.name)) {
      fail(`Agent name must be kebab-case: ${fm.name}`);
    }
  }

  const pluginCommands = walkMarkdown(path.join(pluginDir, 'commands'), ['.md', '.mdc', '.markdown', '.txt']);
  if (pluginCommands.length === 0) fail(`${entry.name}: no command files found under commands/`);
  for (const file of pluginCommands) {
    const fm = parseFrontmatter(file);
    const rel = path.relative(root, file);
    if (!fm || !fm.name || !fm.description) {
      fail(`${rel} needs name and description frontmatter`);
    } else if (!kebabStrict.test(fm.name)) {
      fail(`Command name must be kebab-case: ${fm.name}`);
    }
  }

  const pluginRules = walkMarkdown(path.join(pluginDir, 'rules'), ['.md', '.mdc', '.markdown']);
  if (pluginRules.length === 0) fail(`${entry.name}: no rule files found under rules/`);
  for (const file of pluginRules) {
    const fm = parseFrontmatter(file);
    const rel = path.relative(root, file);
    if (!fm || !fm.description || !('alwaysApply' in fm)) {
      fail(`${rel} needs description and alwaysApply frontmatter`);
    }
  }

  skillDirs = pluginSkills;
  agentFiles = pluginAgents;
  commandFiles = pluginCommands;
  ruleFiles = pluginRules;
}

for (const required of ['LICENSE', 'README.md', 'bin/cli.js']) {
  if (!fs.existsSync(path.join(root, required))) fail(`Missing ${required}`);
}

summarizeAndExit();

function summarizeAndExit() {
  if (errors.length) {
    console.error('Plugin validation failed:\n');
    for (const error of errors) console.error(`- ${error}`);
    process.exit(1);
  }

  console.log('Plugin validation passed.');
  console.log(`Agents: ${agentFiles.length}`);
  console.log(`Skills: ${skillDirs.length}`);
  console.log(`Commands: ${commandFiles.length}`);
  console.log(`Rules: ${ruleFiles.length}`);
  process.exit(0);
}
