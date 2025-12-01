// =============================================================================
// ecosystem.config.js - PM2 Configuration for Crypto Signal Bot
// =============================================================================
// This file configures PM2 process manager for production deployment
// Usage: pm2 start ecosystem.config.js
// =============================================================================

module.exports = {
  apps: [
    {
      name: 'crypto-bot',
      script: 'bot.py',
      interpreter: 'python3',
      cwd: __dirname,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      
      // Restart strategies
      exp_backoff_restart_delay: 100,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 4000,
      
      // Environment variables
      env: {
        NODE_ENV: 'production',
      },
      
      // Logging
      error_file: './logs/error.log',
      out_file: './logs/out.log',
      log_file: './logs/combined.log',
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      
      // Instance configuration
      instances: 1,
      exec_mode: 'fork',
      
      // Kill timeout
      kill_timeout: 5000,
      
      // Listen timeout
      listen_timeout: 10000,
    }
  ],
  
  // Deployment configuration (optional)
  deploy: {
    production: {
      user: 'root',
      host: 'crypto-bot-prod',
      ref: 'origin/main',
      repo: 'git@github.com:galinborisov10-art/Crypto-signal-bot.git',
      path: '/root/Crypto-signal-bot',
      'pre-deploy-local': '',
      'post-deploy': 'pip3 install -r requirements.txt && pm2 reload ecosystem.config.js --env production',
      'pre-setup': '',
      env: {
        NODE_ENV: 'production'
      }
    }
  }
};
