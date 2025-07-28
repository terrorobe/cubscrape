#!/usr/bin/env node
import { existsSync, readFileSync, unlinkSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = dirname(__dirname);

const DEV_LOCK_FILE = join(projectRoot, 'data', '.dev-server.lock');

function stopDevServer() {
    if (!existsSync(DEV_LOCK_FILE)) {
        console.log('ℹ️  No dev server lock file found - server may not be running');
        return;
    }

    try {
        const lockData = JSON.parse(readFileSync(DEV_LOCK_FILE, 'utf8'));
        const {pid} = lockData;

        console.log(`🔍 Found dev server with PID: ${pid}`);

        // Try to kill the process
        try {
            process.kill(pid, 'SIGTERM');
            console.log(`✅ Sent SIGTERM to process ${pid}`);

            // Give it a moment to shut down gracefully
            setTimeout(() => {
                try {
                    // Check if process is still running
                    process.kill(pid, 0);
                    console.log(`⚠️  Process ${pid} still running, sending SIGKILL...`);
                    process.kill(pid, 'SIGKILL');
                } catch {
                    // Process is gone, which is what we want
                    console.log('✅ Dev server stopped successfully');
                }

                // Clean up lock file
                if (existsSync(DEV_LOCK_FILE)) {
                    unlinkSync(DEV_LOCK_FILE);
                    console.log('🔓 Removed dev server lock file');
                }
            }, 2000);

        } catch (error) {
            if (error.code === 'ESRCH') {
                console.log('ℹ️  Process not found - server was already stopped');
                // Clean up stale lock file
                unlinkSync(DEV_LOCK_FILE);
                console.log('🔓 Removed stale lock file');
            } else {
                console.error('❌ Failed to stop dev server:', error.message);
            }
        }

    } catch (error) {
        console.error('❌ Failed to read lock file:', error.message);
        // Clean up invalid lock file
        unlinkSync(DEV_LOCK_FILE);
        console.log('🔓 Removed invalid lock file');
    }
}

console.log('🛑 Stopping dev server...');
stopDevServer();