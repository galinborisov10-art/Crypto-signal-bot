"""
Test suite for BUG C1 - Daily Report Health Check

Tests the fixed daily report health diagnostics:
- Emoji/Unicode normalization
- Primary check (daily_reports.json)
- Fallback check (bot.log with normalized text)
- Failure case (no JSON, no log)
"""

import pytest
import json
import os
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock

# Import the functions we're testing
from system_diagnostics import normalize_text, diagnose_daily_report_issue


class TestEmojiNormalization:
    """Test emoji and Unicode symbol removal"""
    
    def test_emoji_normalization_basic(self):
        """Test: Emoji normalization removes Unicode symbols"""
        input_text = "📊 Daily report sent ✅"
        normalized = normalize_text(input_text)
        
        # Should contain the text without emojis
        assert "daily report sent" in normalized.lower()
        # Should NOT contain emoji characters
        assert "📊" not in normalized
        assert "✅" not in normalized
    
    def test_emoji_normalization_preserves_letters_numbers(self):
        """Test: Normalization preserves letters and numbers"""
        input_text = "Report123 generated"
        normalized = normalize_text(input_text)
        
        assert "report123" in normalized.lower()
        assert "generated" in normalized.lower()
    
    def test_emoji_normalization_preserves_punctuation(self):
        """Test: Normalization preserves punctuation"""
        input_text = "Daily report: sent successfully!"
        normalized = normalize_text(input_text)
        
        assert ":" in normalized
        assert "!" in normalized
    
    def test_emoji_normalization_multiple_emojis(self):
        """Test: Handles multiple emojis"""
        input_text = "🎉 Daily report delivered ✅ 🚀"
        normalized = normalize_text(input_text)
        
        assert "daily report delivered" in normalized.lower()
        assert "🎉" not in normalized
        assert "✅" not in normalized
        assert "🚀" not in normalized


class TestDailyReportPrimaryCheck:
    """Test PRIMARY check using daily_reports.json"""
    
    @pytest.mark.asyncio
    async def test_primary_check_success_today_exists(self):
        """Test: PRIMARY check succeeds when today's report exists in JSON"""
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create daily_reports.json with today's date
            today = datetime.now().strftime('%Y-%m-%d')
            reports_data = {
                "reports": [
                    {
                        "date": today,
                        "timestamp": f"{today}T09:00:00",
                        "total_signals": 5
                    }
                ]
            }
            
            reports_file = os.path.join(tmpdir, 'daily_reports.json')
            with open(reports_file, 'w') as f:
                json.dump(reports_data, f)
            
            # Run diagnostic
            issues = await diagnose_daily_report_issue(base_path=tmpdir)
            
            # Should have NO issues
            assert len(issues) == 0
    
    @pytest.mark.asyncio
    async def test_primary_check_fails_no_today_entry(self):
        """Test: PRIMARY check fails when today's date not in JSON"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create daily_reports.json with old date
            reports_data = {
                "reports": [
                    {
                        "date": "2025-11-24",
                        "timestamp": "2025-11-24T09:00:00",
                        "total_signals": 5
                    }
                ]
            }
            
            reports_file = os.path.join(tmpdir, 'daily_reports.json')
            with open(reports_file, 'w') as f:
                json.dump(reports_data, f)
            
            # Create empty log file
            log_file = os.path.join(tmpdir, 'bot.log')
            with open(log_file, 'w') as f:
                f.write("")
            
            # Run diagnostic
            issues = await diagnose_daily_report_issue(base_path=tmpdir)
            
            # Should have issues (primary failed, fallback also failed)
            assert len(issues) > 0
            assert "Daily report not found" in issues[0]['problem']


class TestDailyReportFallbackCheck:
    """Test FALLBACK check using bot.log with emoji normalization"""
    
    @pytest.mark.asyncio
    async def test_fallback_check_success_with_emoji(self):
        """Test: FALLBACK check succeeds when log contains emoji message"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # No daily_reports.json (primary will fail)
            
            # Create bot.log with emoji message
            log_file = os.path.join(tmpdir, 'bot.log')
            with open(log_file, 'w') as f:
                f.write("2026-01-24 10:00:00 INFO: Bot started\n")
                f.write("2026-01-24 11:00:00 INFO: 📊 Daily report sent successfully ✅\n")
                f.write("2026-01-24 12:00:00 INFO: Processing signals\n")
            
            # Mock logger to capture warning
            with patch('system_diagnostics.logger') as mock_logger:
                # Run diagnostic
                issues = await diagnose_daily_report_issue(base_path=tmpdir)
                
                # Should have NO issues (fallback succeeded)
                assert len(issues) == 0
                
                # Should have logged warning about fallback
                mock_logger.warning.assert_called_with("Daily report detected via log fallback")
    
    @pytest.mark.asyncio
    async def test_fallback_check_detects_various_messages(self):
        """Test: FALLBACK check detects various daily report messages"""
        
        test_messages = [
            "Daily report sent",
            "📊 Daily report generated",
            "Daily report delivered ✅",
            "🎉 DAILY REPORT SENT 🚀",  # uppercase, multiple emojis
        ]
        
        for message in test_messages:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create bot.log with test message
                log_file = os.path.join(tmpdir, 'bot.log')
                with open(log_file, 'w') as f:
                    f.write(f"2026-01-24 11:00:00 INFO: {message}\n")
                
                # Mock logger
                with patch('system_diagnostics.logger'):
                    # Run diagnostic
                    issues = await diagnose_daily_report_issue(base_path=tmpdir)
                    
                    # Should succeed
                    assert len(issues) == 0, f"Failed to detect: {message}"


class TestDailyReportFailureCase:
    """Test FAILURE case when both PRIMARY and FALLBACK fail"""
    
    @pytest.mark.asyncio
    async def test_failure_no_json_no_log(self):
        """Test: Failure when no JSON entry and no log evidence"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty daily_reports.json (no today's entry)
            reports_data = {"reports": []}
            reports_file = os.path.join(tmpdir, 'daily_reports.json')
            with open(reports_file, 'w') as f:
                json.dump(reports_data, f)
            
            # Create bot.log without daily report message
            log_file = os.path.join(tmpdir, 'bot.log')
            with open(log_file, 'w') as f:
                f.write("2026-01-24 10:00:00 INFO: Bot started\n")
                f.write("2026-01-24 12:00:00 INFO: Processing signals\n")
            
            # Run diagnostic
            issues = await diagnose_daily_report_issue(base_path=tmpdir)
            
            # Should have issues
            assert len(issues) > 0
            assert "Daily report not found" in issues[0]['problem']
    
    @pytest.mark.asyncio
    async def test_failure_provides_diagnostic_reason(self):
        """Test: Failure case provides diagnostic information"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # No files at all
            
            # Run diagnostic
            issues = await diagnose_daily_report_issue(base_path=tmpdir)
            
            # Should have issues with diagnostic info
            assert len(issues) > 0
            assert 'problem' in issues[0]
            assert 'root_cause' in issues[0]
            assert 'evidence' in issues[0]
