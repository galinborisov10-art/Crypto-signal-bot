"""
Documentation Links for Common Errors
Maps error types to relevant documentation
"""

DOCUMENTATION_LINKS = {
    # API & Configuration
    'BINANCE_API_KEY': {
        'title': 'Binance API Keys',
        'links': [
            'https://www.binance.com/en/support/faq/how-to-create-api-360002502072',
            'https://academy.binance.com/en/articles/how-to-create-api-keys-on-binance'
        ],
        'security_warning': '⚠️ Never share your API Secret! Never commit keys to git!'
    },
    
    'TELEGRAM_BOT_TOKEN': {
        'title': 'Telegram Bot Token',
        'links': [
            'https://core.telegram.org/bots/tutorial#obtain-your-bot-token',
            'https://core.telegram.org/bots/api'
        ],
        'security_warning': '⚠️ Keep your bot token secret! Anyone with the token can control your bot!'
    },
    
    # Dependencies
    'ccxt': {
        'title': 'CCXT Library',
        'links': [
            'https://docs.ccxt.com/en/latest/install.html',
            'https://github.com/ccxt/ccxt'
        ],
        'install_command': 'pip install ccxt'
    },
    
    'pandas': {
        'title': 'Pandas Library',
        'links': [
            'https://pandas.pydata.org/docs/getting_started/install.html'
        ],
        'install_command': 'pip install pandas'
    },
    
    'python-telegram-bot': {
        'title': 'Python Telegram Bot',
        'links': [
            'https://docs.python-telegram-bot.org/',
            'https://github.com/python-telegram-bot/python-telegram-bot'
        ],
        'install_command': 'pip install python-telegram-bot'
    },
    
    # Database
    'database': {
        'title': 'SQLite Database',
        'links': [
            'https://docs.python.org/3/library/sqlite3.html',
            'https://www.sqlite.org/docs.html'
        ]
    },
    
    # Trading Journal
    'trading_journal': {
        'title': 'Trading Journal Format',
        'links': [
            'https://www.json.org/json-en.html'
        ],
        'note': 'Journal should be a valid JSON array'
    },
    
    # General Python
    'python_environment': {
        'title': 'Python Virtual Environments',
        'links': [
            'https://docs.python.org/3/library/venv.html',
            'https://realpython.com/python-virtual-environments-a-primer/'
        ]
    }
}

def get_documentation(error_key: str) -> dict:
    """Get documentation for specific error"""
    return DOCUMENTATION_LINKS.get(error_key, {
        'title': 'General Documentation',
        'links': ['https://docs.python.org/3/']
    })

def format_documentation(error_key: str) -> str:
    """Format documentation section for error"""
    
    docs = get_documentation(error_key)
    
    output = "📚 Documentation:\n"
    
    if 'title' in docs:
        output += f"  {docs['title']}\n"
    
    if 'links' in docs:
        for link in docs['links']:
            output += f"  → {link}\n"
    
    if 'install_command' in docs:
        output += f"\n💡 Quick install:\n  {docs['install_command']}\n"
    
    if 'security_warning' in docs:
        output += f"\n{docs['security_warning']}\n"
    
    if 'note' in docs:
        output += f"\nℹ️ Note: {docs['note']}\n"
    
    return output

