#!/usr/bin/env node

import { existsSync, readFileSync, unlinkSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = dirname(__dirname);

const DEV_LOCK_FILE = join(projectRoot, 'data', '.dev-server.lock');

function killProcess(pid, name) {
    return new Promise((resolve) => {
        try {
            process.kill(pid, 'SIGTERM');
            console.log(`📤 Sent SIGTERM to ${name} process ${pid}`);

            // Check if process died after 2 seconds
            setTimeout(() => {
                try {
                    process.kill(pid, 0);
                    console.log(`⚠️  ${name} process ${pid} still running, sending SIGKILL...`);
                    process.kill(pid, 'SIGKILL');
                    resolve(true);
                } catch {
                    console.log(`✅ ${name} process ${pid} stopped`);
                    resolve(true);
                }
            }, 2000);
        } catch (error) {
            if (error.code === 'ESRCH') {
                console.log(`ℹ️  ${name} process ${pid} not found - already stopped`);
            } else {
                console.error(`❌ Failed to stop ${name} process:`, error.message);
            }
            resolve(false);
        }
    });
}

async function stopDevServer() {
    if (!existsSync(DEV_LOCK_FILE)) {
        console.log('ℹ️  No dev server lock file found - server may not be running');
        return;
    }

    try {
        const lockData = JSON.parse(readFileSync(DEV_LOCK_FILE, 'utf8'));
        const {pid, vitePid} = lockData;

        console.log(`🔍 Found dev server processes:`);
        console.log(`   Parent PID: ${pid}`);
        console.log(`   Vite PID: ${vitePid || 'unknown'}`);

        // Kill processes in parallel
        const promises = [];

        // Kill Vite process first if we have its PID
        if (vitePid) {
            promises.push(killProcess(vitePid, 'Vite'));
        }

        // Kill parent process
        promises.push(killProcess(pid, 'Parent'));

        // Wait for all processes to be killed
        await Promise.all(promises);

        console.log('✅ All dev server processes stopped');

        // Clean up lock file
        if (existsSync(DEV_LOCK_FILE)) {
            unlinkSync(DEV_LOCK_FILE);
            console.log('🔓 Removed dev server lock file');
        }

    } catch (error) {
        console.error('❌ Failed to read lock file:', error.message);
        // Clean up invalid lock file
        unlinkSync(DEV_LOCK_FILE);
        console.log('🔓 Removed invalid lock file');
    }
}

console.log('🛑 Stopping dev server...');
stopDevServer().then(() => {
    process.exit(0);
}).catch((error) => {
    console.error('❌ Error stopping dev server:', error);
    process.exit(1);
});