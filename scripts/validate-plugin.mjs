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
  const text = fs.readFileSync(filePath, 'utf8');
  if (!text.startsWith('---\n') && !text.startsWith('---\r\n')) {
    return null;
  }
  const end = text.indexOf('\n---', 4);
  if (end === -1) return null;
  const block = text.slice(4, end);
  const data = {};
  for (const line of block.split(/\r?\n/)) {
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

function assertRelativeSafe(value, label) {
  if (typeof value !== 'string') return;
  if (value.includes('..') || path.isAbsolute(value)) {
    fail(`${label} must be a relative path without '..': ${value}`);
  }
}

const kebab = /^[a-z0-9]+(?:[.-][a-z0-9]+)*$/;
const kebabStrict = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

const manifest = readJson('.cursor-plugin/plugin.json');
if (manifest) {
  if (!manifest.name || !kebab.test(manifest.name)) {
    fail('plugin.json name must be lowercase kebab-case');
  }
  if (!manifest.description) fail('plugin.json missing description');
  if (!manifest.version) fail('plugin.json missing version');
  if (!manifest.author || typeof manifest.author !== 'object' || !manifest.author.name) {
    fail('plugin.json author must be an object with name');
  }
  if (manifest.servers) fail('plugin.json must not use undocumented servers field');
  if (Array.isArray(manifest.skills) && manifest.skills.some((s) => s && typeof s === 'object' && 'prompt' in s)) {
    fail('plugin.json skills must be paths, not inline prompt objects');
  }
  if (manifest.logo) {
    assertRelativeSafe(manifest.logo, 'logo');
    const logoPath = path.join(root, manifest.logo);
    if (!fs.existsSync(logoPath)) fail(`Logo not found: ${manifest.logo}`);
  }
  for (const field of ['agents', 'skills', 'rules', 'commands']) {
    const value = manifest[field];
    if (!value) continue;
    const paths = Array.isArray(value) ? value : [value];
    for (const p of paths) {
      if (typeof p !== 'string') continue;
      assertRelativeSafe(p, field);
      if (!fs.existsSync(path.join(root, p))) fail(`Declared ${field} path missing: ${p}`);
    }
  }
}

if (fs.existsSync(path.join(root, '.cursor-plugin/marketplace.json'))) {
  fail('Single-plugin repos should not include .cursor-plugin/marketplace.json');
}

const skillDirs = fs.existsSync(path.join(root, 'skills'))
  ? fs.readdirSync(path.join(root, 'skills'), { withFileTypes: true }).filter((e) => e.isDirectory())
  : [];
if (skillDirs.length === 0) fail('No skills found under skills/*/SKILL.md');
for (const dir of skillDirs) {
  const skillFile = path.join(root, 'skills', dir.name, 'SKILL.md');
  if (!fs.existsSync(skillFile)) {
    fail(`Missing ${path.relative(root, skillFile)}`);
    continue;
  }
  const fm = parseFrontmatter(skillFile);
  if (!fm || !fm.name || !fm.description) {
    fail(`${path.relative(root, skillFile)} needs name and description frontmatter`);
  } else if (!kebabStrict.test(fm.name)) {
    fail(`Skill name must be kebab-case: ${fm.name}`);
  }
}

const agentFiles = walkMarkdown(path.join(root, 'agents'), ['.md', '.mdc', '.markdown']);
if (agentFiles.length === 0) fail('No agent files found under agents/');
for (const file of agentFiles) {
  const fm = parseFrontmatter(file);
  const rel = path.relative(root, file);
  if (!fm || !fm.name || !fm.description) {
    fail(`${rel} needs name and description frontmatter`);
  } else if (!kebabStrict.test(fm.name)) {
    fail(`Agent name must be kebab-case: ${fm.name}`);
  }
  const text = fs.readFileSync(file, 'utf8');
  if (text.includes('mcp::context7')) {
    fail(`${rel} declares undeclared MCP tool mcp::context7`);
  }
}

const commandFiles = walkMarkdown(path.join(root, 'commands'), ['.md', '.mdc', '.markdown', '.txt']);
if (commandFiles.length === 0) fail('No command files found under commands/');
for (const file of commandFiles) {
  const fm = parseFrontmatter(file);
  const rel = path.relative(root, file);
  if (!fm || !fm.name || !fm.description) {
    fail(`${rel} needs name and description frontmatter`);
  } else if (!kebabStrict.test(fm.name)) {
    fail(`Command name must be kebab-case: ${fm.name}`);
  }
}

const ruleFiles = walkMarkdown(path.join(root, 'rules'), ['.md', '.mdc', '.markdown']);
if (ruleFiles.length === 0) fail('No rule files found under rules/');
for (const file of ruleFiles) {
  const fm = parseFrontmatter(file);
  const rel = path.relative(root, file);
  if (!fm || !fm.description || !('alwaysApply' in fm)) {
    fail(`${rel} needs description and alwaysApply frontmatter`);
  }
}

for (const required of ['LICENSE', 'README.md', 'bin/cli.js']) {
  if (!fs.existsSync(path.join(root, required))) fail(`Missing ${required}`);
}

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
