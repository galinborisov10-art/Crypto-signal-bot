module.exports = {
  apps: [
    {
      name: 'crypto-bot',
      script: 'bot.py',
      interpreter: 'python3',
      cwd: '/root/Crypto-signal-bot',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        PYTHONDONTWRITEBYTECODE: '1',
        PYTHONUNBUFFERED: '1'
      },
      output: './logs/crypto-bot-out.log',
      error: './logs/crypto-bot-error.log',
      log: './logs/crypto-bot-combined.log',
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      restart_delay: 5000,
      kill_timeout: 10000,
      exp_backoff_restart_delay: 100,
      max_restarts: 10,
      min_uptime: '30s'
    }
  ]
};
