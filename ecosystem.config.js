module.exports = {
  apps: [{
    name: 'crypto-bot',
    script: 'bot.py',
    interpreter: 'python3',
    // cwd will be auto-detected or use absolute path on server
    cwd: process.env.BOT_PATH || '/root/Crypto-signal-bot',
    
    // Restart settings
    autorestart: true,
    watch: false,
    max_restarts: 10,
    min_uptime: '10s',
    restart_delay: 4000,
    
    // Logging
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_file: './logs/pm2-combined.log',
    time: true,
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    
    // Environment variables
    env: {
      NODE_ENV: 'production',
      PYTHONUNBUFFERED: '1'
    },
    
    // Advanced settings
    max_memory_restart: '500M',
    kill_timeout: 5000,
    listen_timeout: 10000,
    shutdown_with_message: false,
    
    // PM2 monitoring
    instances: 1,
    exec_mode: 'fork',
    
    // Auto restart at 4 AM daily (optional)
    cron_restart: '0 4 * * *'
  }]
};
