"""
Version Management
Bot version and release information
"""

__version__ = "2.0.0"
__release_date__ = "2025-12-19"
__codename__ = "ICT Complete + Security"

VERSION_INFO = {
    'version': __version__,
    'release_date': __release_date__,
    'codename': __codename__,
    'features': [
        'Complete ICT Signal Engine',
        'Fibonacci Analyzer',
        'LuxAlgo Combined Integration',
        '13-Point Unified Output',
        'Universal Analysis Sequence',
        'Chart Generator',
        'Telegram /backtest Command',
        'Real-time 80% TP Alerts',
        'Security Hardening',
        'Rate Limiting',
        'Auto-deployment'
    ],
    'security': [
        'Encrypted token storage',
        'Rate limiting (20/min, 100/hour)',
        'Auto-ban on abuse (3 violations)',
        'Authentication system',
        'Blacklist/Whitelist support',
        'Security monitoring',
        'Threat level assessment',
        'Admin notifications'
    ]
}


def get_version_string() -> str:
    """
    Get formatted version string
    
    Returns:
        Version string (e.g., "v2.0.0 (ICT Complete + Security) - 2025-12-19")
    """
    return f"v{__version__} ({__codename__}) - {__release_date__}"


def get_full_version_info() -> str:
    """
    Get full version information for /version command
    
    Returns:
        Formatted version information with features and security info
    """
    info = f"━━━━━━━━━━━━━━━━━━━━\n"
    info += f"🤖 **ICT Signal Bot**\n"
    info += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    info += f"📦 Version: **{__version__}**\n"
    info += f"📅 Release: **{__release_date__}**\n"
    info += f"🏷️ Codename: **{__codename__}**\n\n"
    
    info += f"✨ **Features:**\n"
    for feature in VERSION_INFO['features']:
        info += f"• {feature}\n"
    
    info += f"\n🔒 **Security:**\n"
    for sec in VERSION_INFO['security']:
        info += f"• {sec}\n"
    
    info += f"\n━━━━━━━━━━━━━━━━━━━━"
    
    return info


def get_version_dict() -> dict:
    """
    Get version information as dictionary
    
    Returns:
        Dictionary with version information
    """
    return VERSION_INFO.copy()


def get_security_features() -> list:
    """
    Get list of security features
    
    Returns:
        List of security features
    """
    return VERSION_INFO['security'].copy()


def get_bot_features() -> list:
    """
    Get list of bot features
    
    Returns:
        List of bot features
    """
    return VERSION_INFO['features'].copy()
