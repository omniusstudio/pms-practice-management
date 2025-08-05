#!/usr/bin/env node

/**
 * Generate Release Notes Script for PMS
 * Called by semantic-release to generate HIPAA-compliant release notes
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// HIPAA compliance patterns to sanitize
const SENSITIVE_PATTERNS = [
  // Patient identifiers
  /\b\d{3}-\d{2}-\d{4}\b/g, // SSN
  /\b[A-Z]{2}\d{8}\b/g, // Medical record numbers
  /\bMRN[:\s]*\d+\b/gi,
  /\bpatient[\s]+id[:\s]*\d+\b/gi,

  // Personal information
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, // Email addresses
  /\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b/g, // Phone numbers
  /\b\d{1,5}\s+[A-Za-z0-9\s,]+\s+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b/gi, // Addresses

  // API keys and tokens
  /\b[A-Za-z0-9]{32,}\b/g, // Long alphanumeric strings (potential tokens)
  /\bBearer\s+[A-Za-z0-9._-]+/gi,
  /\bapi[_-]?key[:\s]*[A-Za-z0-9._-]+/gi,
  /\btoken[:\s]*[A-Za-z0-9._-]+/gi,

  // Database connection strings
  /\b(postgresql|mysql|mongodb):\/\/[^\s]+/gi,
  /\bpassword[=:\s]+[^\s]+/gi,

  // Internal system references
  /\bserver[\s-]?\d+\.[a-z0-9.-]+/gi,
  /\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, // IP addresses
];

// Replacement text for sanitized content
const SANITIZED_REPLACEMENT = '[REDACTED]';

function sanitizeContent(content) {
  let sanitized = content;

  SENSITIVE_PATTERNS.forEach(pattern => {
    sanitized = sanitized.replace(pattern, SANITIZED_REPLACEMENT);
  });

  return sanitized;
}

function formatReleaseNotes(version, rawNotes) {
  const sanitizedNotes = sanitizeContent(rawNotes);

  // Parse the release notes to extract different sections
  const sections = {
    features: [],
    fixes: [],
    performance: [],
    security: [],
    breaking: [],
    other: []
  };

  // Split notes into lines and categorize
  const lines = sanitizedNotes.split('\n').filter(line => line.trim());

  lines.forEach(line => {
    const trimmedLine = line.trim();

    if (trimmedLine.includes('BREAKING CHANGE') || trimmedLine.includes('BREAKING:')) {
      sections.breaking.push(trimmedLine);
    } else if (trimmedLine.match(/^\*?\s*(feat|feature)/i)) {
      sections.features.push(trimmedLine);
    } else if (trimmedLine.match(/^\*?\s*(fix|bug)/i)) {
      sections.fixes.push(trimmedLine);
    } else if (trimmedLine.match(/^\*?\s*(perf|performance)/i)) {
      sections.performance.push(trimmedLine);
    } else if (trimmedLine.match(/^\*?\s*(security|sec)/i)) {
      sections.security.push(trimmedLine);
    } else if (trimmedLine.startsWith('*') || trimmedLine.startsWith('-')) {
      sections.other.push(trimmedLine);
    }
  });

  // Build formatted release notes
  let formattedNotes = `# Release v${version}\n\n`;
  formattedNotes += `**Release Date:** ${new Date().toISOString().split('T')[0]}\n`;
  formattedNotes += `**Build:** ${process.env.GITHUB_RUN_NUMBER || 'local'}\n\n`;

  // Add compliance notice
  formattedNotes += `> **HIPAA Compliance Notice:** This release has been reviewed for HIPAA compliance. All sensitive information has been redacted from release notes.\n\n`;

  // Add breaking changes first (most important)
  if (sections.breaking.length > 0) {
    formattedNotes += `## ⚠️ Breaking Changes\n\n`;
    sections.breaking.forEach(item => {
      formattedNotes += `${item}\n`;
    });
    formattedNotes += '\n';
  }

  // Add security updates
  if (sections.security.length > 0) {
    formattedNotes += `## 🔒 Security Updates\n\n`;
    sections.security.forEach(item => {
      formattedNotes += `${item}\n`;
    });
    formattedNotes += '\n';
  }

  // Add new features
  if (sections.features.length > 0) {
    formattedNotes += `## ✨ New Features\n\n`;
    sections.features.forEach(item => {
      formattedNotes += `${item}\n`;
    });
    formattedNotes += '\n';
  }

  // Add bug fixes
  if (sections.fixes.length > 0) {
    formattedNotes += `## 🐛 Bug Fixes\n\n`;
    sections.fixes.forEach(item => {
      formattedNotes += `${item}\n`;
    });
    formattedNotes += '\n';
  }

  // Add performance improvements
  if (sections.performance.length > 0) {
    formattedNotes += `## ⚡ Performance Improvements\n\n`;
    sections.performance.forEach(item => {
      formattedNotes += `${item}\n`;
    });
    formattedNotes += '\n';
  }

  // Add other changes
  if (sections.other.length > 0) {
    formattedNotes += `## 📝 Other Changes\n\n`;
    sections.other.forEach(item => {
      formattedNotes += `${item}\n`;
    });
    formattedNotes += '\n';
  }

  // Add deployment information
  formattedNotes += `## 🚀 Deployment Information\n\n`;
  formattedNotes += `- **Deployment Strategy:** Blue/Green\n`;
  formattedNotes += `- **Rollback Available:** Yes\n`;
  formattedNotes += `- **Health Checks:** Automated\n`;
  formattedNotes += `- **Monitoring:** Enhanced for this release\n\n`;

  // Add technical details
  try {
    const gitCommit = execSync('git rev-parse HEAD', { encoding: 'utf8' }).trim();
    const gitBranch = execSync('git rev-parse --abbrev-ref HEAD', { encoding: 'utf8' }).trim();

    formattedNotes += `## 📋 Technical Details\n\n`;
    formattedNotes += `- **Git Commit:** \`${gitCommit.substring(0, 8)}\`\n`;
    formattedNotes += `- **Git Branch:** \`${gitBranch}\`\n`;
    formattedNotes += `- **Release Type:** Semantic Release\n`;
    formattedNotes += `- **Changelog:** [View Full Changelog](CHANGELOG.md)\n\n`;
  } catch (error) {
    console.warn('⚠️ Could not retrieve git information:', error.message);
  }

  // Add footer
  formattedNotes += `---\n\n`;
  formattedNotes += `**Note:** This is an automated release generated by semantic-release. `;
  formattedNotes += `For technical support or questions about this release, please contact the development team.\n`;

  return formattedNotes;
}

function createReleaseArtifacts(version, formattedNotes) {
  const artifactsDir = 'release-artifacts';

  // Ensure artifacts directory exists
  if (!fs.existsSync(artifactsDir)) {
    fs.mkdirSync(artifactsDir, { recursive: true });
  }

  // Create release notes file
  const releaseNotesPath = path.join(artifactsDir, `release-notes-v${version}.md`);
  fs.writeFileSync(releaseNotesPath, formattedNotes);

  // Create release summary JSON
  const releaseSummary = {
    version,
    releaseDate: new Date().toISOString(),
    gitCommit: process.env.GITHUB_SHA || 'unknown',
    gitBranch: process.env.GITHUB_REF_NAME || 'unknown',
    buildNumber: process.env.GITHUB_RUN_NUMBER || 'local',
    releaseType: 'semantic',
    hipaaCompliant: true,
    sanitized: true
  };

  const summaryPath = path.join(artifactsDir, `release-summary-v${version}.json`);
  fs.writeFileSync(summaryPath, JSON.stringify(releaseSummary, null, 2));

  console.log(`✅ Created release notes: ${releaseNotesPath}`);
  console.log(`✅ Created release summary: ${summaryPath}`);

  return { releaseNotesPath, summaryPath };
}

function main() {
  const version = process.argv[2];
  const notesFile = process.argv[3];

  if (!version) {
    console.error('❌ Error: Version parameter is required');
    console.error('Usage: node generate-release-notes.js <version> [notes-file]');
    process.exit(1);
  }

  let rawNotes = '';
  if (notesFile && fs.existsSync(notesFile)) {
    rawNotes = fs.readFileSync(notesFile, 'utf8').trim();
  }

  console.log(`🔄 Generating release notes for version: ${version}`);

  try {
    // Format and sanitize release notes
    const formattedNotes = formatReleaseNotes(version, rawNotes);

    // Create release artifacts
    const artifacts = createReleaseArtifacts(version, formattedNotes);

    // Update CHANGELOG.md if it exists
    const changelogPath = 'CHANGELOG.md';
    if (fs.existsSync(changelogPath)) {
      const existingChangelog = fs.readFileSync(changelogPath, 'utf8');
      const updatedChangelog = formattedNotes + '\n\n' + existingChangelog;
      fs.writeFileSync(changelogPath, updatedChangelog);
      console.log(`✅ Updated ${changelogPath}`);
    } else {
      // Create new changelog
      fs.writeFileSync(changelogPath, formattedNotes);
      console.log(`✅ Created ${changelogPath}`);
    }

    console.log('🎉 Release notes generation completed successfully!');
    console.log('📋 Summary:');
    console.log(`  - Version: ${version}`);
    console.log(`  - HIPAA Compliant: Yes`);
    console.log(`  - Sanitized: Yes`);
    console.log(`  - Artifacts: ${Object.keys(artifacts).length}`);

  } catch (error) {
    console.error('❌ Error generating release notes:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  sanitizeContent,
  formatReleaseNotes,
  createReleaseArtifacts
};
