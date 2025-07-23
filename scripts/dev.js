#!/usr/bin/env node
import { spawn } from 'child_process';
import { statSync, existsSync, readdirSync } from 'fs';
import { join } from 'path';

// Check if database needs rebuilding
function shouldRebuildDatabase() {
    const dbPath = join('data', 'games.db');

    if (!existsSync(dbPath)) {
        console.log('📦 Database does not exist, will build it...');
        return true;
    }

    const dbMtime = statSync(dbPath).mtime;

    // Check if any JSON files or schema.sql are newer than the database
    const dataDir = 'data';
    const files = readdirSync(dataDir);

    for (const file of files) {
        if (file.endsWith('.json') || file === 'schema.sql') {
            const filePath = join(dataDir, file);
            const fileMtime = statSync(filePath).mtime;

            if (fileMtime > dbMtime) {
                console.log(`🔄 Database needs rebuild - ${file} is newer`);
                return true;
            }
        }
    }

    console.log('✅ Database is up to date');
    return false;
}

// Run a command and wait for it to complete
function runCommand(command, args = []) {
    return new Promise((resolve, reject) => {
        const proc = spawn(command, args, {
            stdio: 'inherit',
            shell: true
        });

        proc.on('close', (code) => {
            if (code !== 0) {
                reject(new Error(`Command failed with code ${code}`));
            } else {
                resolve();
            }
        });

        proc.on('error', reject);
    });
}

async function main() {
    console.log('🚀 Starting development environment...\n');

    try {
        // Build database if needed
        if (shouldRebuildDatabase()) {
            console.log('📦 Building SQLite database from JSON files...');
            await runCommand('uv', ['run', 'cubscrape', 'build-db']);
            console.log('✅ Database built successfully\n');
        }

        // Start Vite dev server
        console.log('🌐 Starting Vue dev server...');
        console.log('Press Ctrl+C to stop the server\n');

        await runCommand('vite');

    } catch (error) {
        console.error('\n❌ Error:', error.message);
        process.exit(1);
    }
}

// Handle Ctrl+C gracefully
process.on('SIGINT', () => {
    console.log('\n\n👋 Server stopped');
    process.exit(0);
});

main();