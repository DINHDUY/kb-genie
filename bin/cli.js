#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const PLUGIN_DIR = path.resolve(__dirname, '..');
const AGENTS_DIR = path.join(PLUGIN_DIR, 'plugins/kb-genie/agents');
const KB_TEMPLATES_DIR = path.join(PLUGIN_DIR, 'templates/knowledge-base');

function printUsage() {
  console.log(`
kb-genie — KB Genie Cursor Plugin

USAGE:
  npx @dtranllc/kb-genie             Show usage
  npx @dtranllc/kb-genie init        Copy knowledge-base template to current directory
  npx @dtranllc/kb-genie info        Show agent inventory and plugin details

INVOKE AGENTS IN CURSOR:
  @kb-orchestrator   — Run full ingestion pipeline on a knowledge base directory
  @kb-ingestion      — Convert raw documents to clean Markdown
  @kb-summarizer     — Generate structured document summaries
  @kb-chunker        — Split documents into semantic chunks
  @kb-concept-distiller — Maintain living concept wiki
  @kb-indexer        — Rebuild authoritative index.yaml
  @kb-graph-builder  — Build knowledge graph (optional)
  @kb-critic         — Run quality spot-checks
`);
}

function printInfo() {
  console.log('\nkb-genie v' + require(path.join(PLUGIN_DIR, 'package.json')).version);
  console.log('KB Genie — Cursor Agent Plugin\n');

  const agents = fs.readdirSync(AGENTS_DIR).filter(f => f.endsWith('.md'));
  console.log('Agents (' + agents.length + '):');
  agents.forEach(file => {
    const frontmatter = fs.readFileSync(path.join(AGENTS_DIR, file), 'utf8').split('---')[1];
    const nameMatch = frontmatter.match(/name:\s*(.+)/);
    const descMatch = frontmatter.match(/description:\s*["'](.+?)["']/);
    const modelMatch = frontmatter.match(/model:\s*(.+)/);
    const name = nameMatch ? nameMatch[1].trim() : file.replace('.md', '');
    const model = modelMatch ? modelMatch[1].trim() : '?';
    const desc = descMatch ? descMatch[1].trim() : '';
    console.log(`  @${name}  (${model})  ${desc.substring(0, 80)}...`);
  });

  console.log('\nInvoke in Cursor with @agent-name.\n');
}

function installKBTemplate(targetDir) {
  if (!fs.existsSync(KB_TEMPLATES_DIR)) {
    console.error('Knowledge base templates not found. Skipping template copy.');
    return;
  }

  const targetKB = path.join(targetDir, 'knowledge-base');
  if (fs.existsSync(targetKB)) {
    console.log(`Knowledge base directory already exists at ${targetKB}. Skipping.`);
    return;
  }

  fs.cpSync(KB_TEMPLATES_DIR, targetKB, { recursive: true });
  console.log(`Knowledge base template copied to ${targetKB}`);
}

function main() {
  const command = process.argv[2] || '';

  switch (command) {
    case 'init':
    case 'install': {
      const target = process.cwd();
      console.log('Copying knowledge-base template...');
      console.log('Target directory: ' + target);
      installKBTemplate(target);
      console.log('\nThis command only creates a knowledge-base/ folder.');
      console.log('Install the Cursor plugin via Dashboard → Plugins → Import from Repo.\n');
      console.log('Next steps:');
      console.log('1. Place your documents (PDF, DOCX, HTML, Markdown) in knowledge-base/raw/');
      console.log('2. Open Cursor and invoke @kb-orchestrator');
      console.log('3. Provide the knowledge base root path');
      break;
    }
    case 'info':
      printInfo();
      break;
    default:
      printUsage();
  }
}

main();
