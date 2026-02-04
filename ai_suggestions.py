"""
AI-Powered Diagnostic Suggestions
Provides intelligent suggestions for common errors
Falls back to rule-based suggestions if no AI API available
"""

import os
from typing import Dict, List, Optional

class AISuggestionEngine:
    """Generate AI-powered suggestions for errors"""
    
    def __init__(self):
        self.has_openai = False
        
        # Try to import OpenAI (optional)
        try:
            import openai
            self.openai = openai
            
            # Check for API key
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai.api_key = api_key
                self.has_openai = True
        except ImportError:
            pass
    
    def get_suggestion(self, error_type: str, error_message: str, context: Dict = None) -> str:
        """Get AI suggestion for error"""
        
        if self.has_openai:
            return self._get_ai_suggestion(error_type, error_message, context)
        else:
            return self._get_rule_based_suggestion(error_type, error_message, context)
    
    def _get_ai_suggestion(self, error_type: str, error_message: str, context: Dict) -> str:
        """Get suggestion from OpenAI API"""
        
        try:
            prompt = f"""You are a helpful assistant debugging a crypto trading bot.

Error Type: {error_type}
Error Message: {error_message}
Context: {context}

Provide:
1. Brief explanation of why this error occurs
2. 2-3 most common causes
3. Step-by-step fix suggestion

Keep response under 200 words, be concise and actionable."""

            response = self.openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )
            
            return "🤖 AI Suggestion:\n" + response.choices[0].message.content
        except Exception as e:
            return self._get_rule_based_suggestion(error_type, error_message, context)
    
    def _get_rule_based_suggestion(self, error_type: str, error_message: str, context: Dict) -> str:
        """Get rule-based suggestion (fallback)"""
        
        suggestions = {
            'config': """🤖 Common Causes:
  • Configuration file not created or corrupted
  • Environment variables not loaded
  • Values commented out or missing
  
💡 Typical fix:
  1. Check if .env file exists
  2. Verify all required keys are present
  3. Ensure no '#' comments before active values
  4. Restart bot after changes""",
            
            'import': """🤖 Common Causes:
  • Python package not installed
  • Wrong virtual environment activated
  • Package version incompatibility
  
💡 Typical fix:
  1. Activate virtual environment: source venv/bin/activate
  2. Install missing package: pip install <package>
  3. Check requirements.txt is up to date
  4. Verify Python version compatibility""",
            
            'database': """🤖 Common Causes:
  • Database file corrupted or locked
  • Missing table or schema changes
  • Concurrent access without locks
  
💡 Typical fix:
  1. Check if .db file exists and has permissions
  2. Stop all bot instances to release locks
  3. Backup and recreate database if corrupted
  4. Run database migrations if schema changed""",
            
            'api': """🤖 Common Causes:
  • Invalid or expired API credentials
  • API rate limit exceeded
  • Network connectivity issues
  • API endpoint changed or deprecated
  
💡 Typical fix:
  1. Verify API keys are valid and not expired
  2. Check API rate limits and usage
  3. Test network connection to API endpoint
  4. Review API documentation for changes""",
            
            'file': """🤖 Common Causes:
  • File doesn't exist at expected path
  • Permission denied (wrong user/group)
  • Disk full or read-only filesystem
  
💡 Typical fix:
  1. Verify file path is correct
  2. Check file permissions: ls -l <file>
  3. Check disk space: df -h
  4. Ensure bot has read/write access""",
        }
        
        # Match error type to suggestion category
        error_lower = error_type.lower() + " " + error_message.lower()
        
        for key, suggestion in suggestions.items():
            if key in error_lower:
                return suggestion
        
        # Default suggestion
        return """🤖 General Debugging Steps:
  • Check recent log files for detailed error messages
  • Verify all dependencies are installed
  • Ensure configuration files are valid
  • Try restarting the bot
  • Check system resources (disk, memory)
  
💡 For more help:
  • Review bot logs: journalctl -u crypto-bot -n 100
  • Check system diagnostics: /health in Telegram
  • Consult documentation for specific error"""

