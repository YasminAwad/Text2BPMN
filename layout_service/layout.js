/**
 * Reads BPMN XML from stdin, applies auto-layout, writes to stdout.
 * 
 * Usage:
 *   node layout.js < input.bpmn > output.bpmn
 *   echo "<xml>...</xml>" | node layout.js
 */

const fs = require('fs');
const { layoutProcess } = require('bpmn-auto-layout');

let inputXml = '';

process.stdin.setEncoding('utf8');

process.stdin.on('data', (chunk) => {
  inputXml += chunk;
});

process.stdin.on('end', async () => {
  try {
    // Validate input
    if (!inputXml || inputXml.trim().length === 0) {
      console.error('Error: No input provided');
      process.exit(1);
    }

    // Apply auto-layout
    const layoutedXml = await layoutProcess(inputXml);

    process.stdout.write(layoutedXml);
    process.exit(0);

  } catch (error) {
    console.error('Error applying auto-layout:', error.message);
    process.exit(1);
  }
});

process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error.message);
  process.exit(1);
});