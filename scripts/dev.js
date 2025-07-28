#!/usr/bin/env node
import { spawn } from 'child_process';
import { statSync, existsSync, readdirSync, writeFileSync, unlinkSync, readFileSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = dirname(__dirname);

// Lock file management
const DEV_LOCK_FILE = join(projectRoot, 'data', '.dev-server.lock');

function createLockFile() {
    // Check if lock file already exists
    if (existsSync(DEV_LOCK_FILE)) {
        try {
            const lockData = JSON.parse(readFileSync(DEV_LOCK_FILE, 'utf8'));
            const {pid} = lockData;

            // Check if process is still running
            try {
                // On Unix, sending signal 0 checks if process exists
                process.kill(pid, 0);
                console.log(`✅ Dev server is already running (PID: ${pid})`);
                console.log('   Access at: http://localhost:5173');
                console.log('   Stop with: npm run stop-dev');
                process.exit(0);
            } catch {
                // Process no longer exists, remove stale lock file
                console.log(`⚠️  Removing stale dev server lock file from PID ${pid}`);
                unlinkSync(DEV_LOCK_FILE);
            }
        } catch {
            // Invalid lock file, remove it
            console.log('⚠️  Removing invalid dev server lock file');
            unlinkSync(DEV_LOCK_FILE);
        }
    }

    // Create new lock file
    const lockData = {
        pid: process.pid,
        startTime: new Date().toISOString(),
        command: 'npm run dev'
    };

    writeFileSync(DEV_LOCK_FILE, JSON.stringify(lockData, null, 2));
    console.log(`🔒 Created dev server lock file (PID: ${process.pid})`);
}

function removeLockFile() {
    // Kill all child processes first
    killChildProcesses();

    if (existsSync(DEV_LOCK_FILE)) {
        try {
            unlinkSync(DEV_LOCK_FILE);
            console.log('🔓 Removed dev server lock file');
        } catch (error) {
            console.warn('⚠️  Failed to remove dev server lock file:', error.message);
        }
    }
}

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

// Store child processes for cleanup
let childProcesses = [];

// Run a command and wait for it to complete
function runCommand(command, args = []) {
    return new Promise((resolve, reject) => {
        const proc = spawn(command, args, {
            stdio: 'inherit',
            shell: true,
            // Create new process group so we can kill the entire group
            detached: false
        });

        // Track child process for cleanup
        childProcesses.push(proc);

        // Monitor child process and clean up lock file if it dies unexpectedly
        proc.on('close', (code, signal) => {
            // Remove from tracking
            childProcesses = childProcesses.filter(p => p.pid !== proc.pid);

            if (signal) {
                console.log(`\n⚠️  ${command} process killed by signal ${signal}`);
                removeLockFile();
            }

            if (code !== 0) {
                reject(new Error(`Command failed with code ${code}`));
            } else {
                resolve();
            }
        });

        proc.on('error', (error) => {
            // Remove from tracking
            childProcesses = childProcesses.filter(p => p.pid !== proc.pid);
            removeLockFile();
            reject(error);
        });
    });
}

// Kill all child processes
function killChildProcesses() {
    childProcesses.forEach(proc => {
        try {
            if (!proc.killed) {
                console.log(`🔄 Killing child process ${proc.pid}`);
                proc.kill('SIGTERM');

                // If SIGTERM doesn't work after 2 seconds, use SIGKILL
                setTimeout(() => {
                    if (!proc.killed) {
                        console.log(`💀 Force killing child process ${proc.pid}`);
                        proc.kill('SIGKILL');
                    }
                }, 2000);
            }
        } catch {
            // Process might already be dead, ignore
        }
    });
    childProcesses = [];
}

async function main() {
    console.log('🚀 Starting development environment...\n');

    try {
        // Create lock file to prevent multiple instances
        createLockFile();

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
        removeLockFile();
        process.exit(1);
    }
}

// Handle graceful shutdown for all termination signals
function setupGracefulShutdown() {
    const cleanup = (signal) => {
        console.log(`\n\n👋 Received ${signal}, shutting down dev server...`);
        removeLockFile();
        process.exit(0);
    };

    // Handle various termination signals
    process.on('SIGINT', () => cleanup('SIGINT'));   // Ctrl+C
    process.on('SIGTERM', () => cleanup('SIGTERM')); // Termination signal
    process.on('SIGHUP', () => cleanup('SIGHUP'));   // Hangup signal

    // Handle uncaught exceptions
    process.on('uncaughtException', (error) => {
        console.error('\n❌ Uncaught exception:', error.message);
        removeLockFile();
        process.exit(1);
    });

    // Handle unhandled promise rejections
    process.on('unhandledRejection', (error) => {
        console.error('\n❌ Unhandled rejection:', error.message);
        removeLockFile();
        process.exit(1);
    });
}

// Set up signal handlers before starting
setupGracefulShutdown();

main();